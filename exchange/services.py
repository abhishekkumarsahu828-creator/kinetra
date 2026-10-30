"""Authoritative business operations. Never call state changes via GET."""
from datetime import timedelta
from decimal import Decimal
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import (Membership, Credential, Booking, ConditionReport, Incident,
                     AuditEvent, Notification, Resource, Blackout)

BLOCKING={'approved','checkin_pending','active','return_pending'}
OPEN={'requested','waitlisted','approved','checkin_pending','active','return_pending'}
REVIEWER_ROLES={'owner','manager','admin'}


def membership(user, organisation, roles=None):
    if not user.is_authenticated: raise PermissionDenied('Sign in is required.')
    item=Membership.objects.filter(user=user,organisation=organisation,status=Membership.Status.ACTIVE).first()
    if item is None or (roles and item.role not in roles):
        raise PermissionDenied('Your verified organisation membership does not allow this action.')
    return item


def reviewer(user, resource):
    item=membership(user,resource.organisation,REVIEWER_ROLES)
    if item.role == 'owner' and resource.owner_id != user.pk:
        raise PermissionDenied('Owners can only review their own resources.')
    return item


def audit(org, user, verb, obj, **details):
    return AuditEvent.objects.create(organisation=org, actor=user,verb=verb,
       object_type=obj.__class__.__name__,object_id=obj.pk,details=details)


def notify(user,title,body,booking=None):
    return Notification.objects.create(user=user,title=title,body=body,
                                      link=reverse('booking_detail',args=[booking.pk]) if booking else '')


def credential_status(user,resource):
    member=Membership.objects.filter(user=user,organisation=resource.organisation,status='active').first()
    if member is None: return False,'Verified membership is required.'
    required=resource.required_training.strip()
    if required:
        credential=Credential.objects.filter(member=member,title__iexact=required,status='verified').first()
        if not credential or (credential.expires_at and credential.expires_at < timezone.localdate()):
            return False,f'Verified training required: {required}.'
    return True,'Eligibility requirements satisfied.'


def schedule_status(resource,start,end):
    if start is None or end is None or timezone.is_naive(start) or timezone.is_naive(end):
        return False,'A valid start and end time are required.'
    if start >= end: return False,'End time must be after start time.'
    if start < timezone.now()-timedelta(minutes=2): return False,'Choose a future booking time.'
    if start > timezone.now()+timedelta(days=resource.advance_booking_days):
        return False,f'Bookings can be requested up to {resource.advance_booking_days} days in advance.'
    if end-start > timedelta(hours=resource.max_hours): return False,f'Maximum duration: {resource.max_hours} hours.'
    local_start=timezone.localtime(start)
    local_end=timezone.localtime(end)
    if local_start.date()!=local_end.date(): return False,'Bookings must start and finish on the same day.'
    if str(local_start.weekday()) not in resource.available_days.split(','):
        return False,'Resource is not offered on this day.'
    if local_start.time() < resource.open_time or local_end.time() > resource.close_time:
        return False,f'Resource hours: {resource.open_time:%H:%M}–{resource.close_time:%H:%M}.'
    if resource.status!='active': return False,'Resource is currently unavailable.'
    if Blackout.objects.filter(resource=resource,start__lt=end,end__gt=start).exists():
        return False,'This period is blocked for maintenance or institutional use.'
    return True,''


def active_conflicts(resource,start,end,exclude=None):
    qs=Booking.objects.filter(resource=resource,status__in=BLOCKING,start__lt=end,end__gt=start)
    if exclude: qs=qs.exclude(pk=exclude)
    return qs.exists()


def recent_usage_hours(user,resource,days=30):
    period=timezone.now()-timedelta(days=days)
    qs=Booking.objects.filter(borrower=user,resource=resource,status__in={'approved','checkin_pending','active','return_pending','completed'},end__gte=period)
    return sum((b.end-b.start).total_seconds()/3600 for b in qs.only('start','end'))


def quotas_ok(user,resource,start,end):
    org=resource.organisation
    active=Booking.objects.filter(borrower=user,resource__organisation=org,status__in=OPEN).count()
    if active >= org.max_active_bookings:
        return False,f'Fair-access limit: {org.max_active_bookings} open bookings per person in this organisation.'
    week_ago=timezone.now()-timedelta(days=7)
    week=Booking.objects.filter(borrower=user,resource=resource,
        status__in={'approved','checkin_pending','active','return_pending','completed'},end__gte=week_ago)
    used=sum((b.end-b.start).total_seconds()/3600 for b in week.only('start','end'))
    hours=(end-start).total_seconds()/3600
    if used+hours > resource.weekly_hours_limit:
        return False,f'Weekly fair-use limit: {resource.weekly_hours_limit} hours for this resource.'
    return True,''


@transaction.atomic
def request_booking(user,resource_id,start,end,purpose):
    resource=Resource.objects.select_for_update().select_related('organisation').get(pk=resource_id)
    allowed,message=credential_status(user,resource)
    if not allowed: raise ValidationError(message)
    allowed,message=schedule_status(resource,start,end)
    if not allowed: raise ValidationError(message)
    allowed,message=quotas_ok(user,resource,start,end)
    if not allowed: raise ValidationError(message)
    # A user should not be able to reserve the exact same resource twice for overlapping times.
    if Booking.objects.filter(resource=resource,borrower=user,status__in=OPEN,start__lt=end,end__gt=start).exists():
        raise ValidationError('You already have an overlapping open request for this resource.')
    conflict=active_conflicts(resource,start,end)
    status=Booking.Status.WAITLISTED if conflict else Booking.Status.REQUESTED
    booking=Booking.objects.create(resource=resource,borrower=user,start=start,end=end,
        purpose=purpose,status=status,
        decision_reason='An approved booking already occupies this period; placed in a fair waiting list.' if conflict else '')
    audit(resource.organisation,user,'booking.requested',booking,status=status)
    notify(user,'Request received', 'You are waitlisted because this time is occupied.' if conflict else 'Your request is awaiting owner review.',booking)
    notify(resource.owner,'New resource request',f'{user.get_username()} requested {resource.name}.',booking)
    return booking


@transaction.atomic
def decide_booking(user,booking_id,action,reason=''):
    # Lock resource first in all booking mutations to serialise across requests for a resource.
    base=get_object_or_404(Booking.objects.select_related('resource'),pk=booking_id)
    resource=Resource.objects.select_for_update().get(pk=base.resource_id)
    reviewer(user,resource)
    booking=Booking.objects.select_for_update().select_related('borrower').get(pk=booking_id)
    if booking.borrower_id==user.pk:
        raise ValidationError('You cannot approve or reject your own booking.')
    if booking.status not in ('requested','waitlisted'):
        raise ValidationError('This request has already been processed.')
    if action not in ('approve','reject','waitlist'):
        raise ValidationError('Unknown decision.')
    if action in ('reject','waitlist') and not reason.strip():
        raise ValidationError('Please explain this decision.')
    if action=='approve':
        ok,msg=credential_status(booking.borrower,resource)
        if not ok: raise ValidationError(msg)
        ok,msg=schedule_status(resource,booking.start,booking.end)
        if not ok: raise ValidationError(msg)
        if active_conflicts(resource,booking.start,booking.end,booking.pk):
            raise ValidationError('Another booking already occupies this slot. Choose Waitlist.')
        booking.status='approved'
        booking.decision_reason=reason.strip() or 'Approved by an authorised reviewer.'
    elif action=='reject':
        booking.status='rejected'
        booking.decision_reason=reason.strip()
    else:
        booking.status='waitlisted'
        booking.decision_reason=reason.strip()
    booking.reviewed_by=user
    booking.reviewed_at=timezone.now()
    booking.save(update_fields=['status','decision_reason','reviewed_by','reviewed_at','updated_at'])
    audit(resource.organisation,user,'booking.'+action,booking,reason=booking.decision_reason)
    notify(booking.borrower,f'Request {booking.get_status_display().lower()}',booking.decision_reason,booking)
    if action=='reject': promote_waitlist(resource,booking.start,booking.end)
    return booking


def promote_waitlist(resource,start,end):
    """Suggest a next fair candidate for HUMAN review; never silently grants access."""
    candidates=Booking.objects.filter(resource=resource,status='waitlisted',start__lt=end,end__gt=start).select_related('borrower')
    if not candidates.exists(): return None
    if active_conflicts(resource,start,end): return None
    viable=[]
    for b in candidates:
        ok,_=credential_status(b.borrower,resource)
        if ok and schedule_status(resource,b.start,b.end)[0] and not active_conflicts(resource,b.start,b.end,b.pk):
            viable.append(b)
    if not viable: return None
    days=resource.organisation.fair_usage_days
    candidate=min(viable,key=lambda b:(recent_usage_hours(b.borrower,resource,days),b.created_at,b.pk))
    candidate.status='requested'
    candidate.decision_reason='An opening is available. Awaiting an authorised manager decision; lower recent usage takes priority.'
    candidate.save(update_fields=['status','decision_reason','updated_at'])
    audit(resource.organisation,None,'waitlist.promoted_for_review',candidate,policy='recent_usage_then_request_time')
    notify(candidate.borrower,'Waitlist update','A slot may be available. The owner will review your request.',candidate)
    notify(resource.owner,'Waitlisted request ready','A waitlisted request is ready for review.',candidate)
    return candidate


@transaction.atomic
def cancel_booking(user,booking_id,reason=''):
    base=get_object_or_404(Booking.objects.select_related('resource'),pk=booking_id)
    resource=Resource.objects.select_for_update().get(pk=base.resource_id)
    booking=Booking.objects.select_for_update().get(pk=booking_id)
    is_owner_action=booking.borrower_id!=user.pk
    if is_owner_action:
        reviewer(user,resource)
        if not reason.strip(): raise ValidationError('An owner cancellation must include a reason.')
    if booking.status not in ('requested','waitlisted','approved'):
        raise ValidationError('This booking cannot be cancelled in its current state.')
    previous=booking.status
    booking.status='cancelled'
    booking.decision_reason=reason.strip() or 'Cancelled by borrower.'
    booking.save(update_fields=['status','decision_reason','updated_at'])
    audit(resource.organisation,user,'booking.cancelled',booking,previous_status=previous,reason=booking.decision_reason)
    notify(booking.borrower,'Booking cancelled',f'{resource.name}: {booking.decision_reason}',booking)
    if previous=='approved': promote_waitlist(resource,booking.start,booking.end)
    return booking


@transaction.atomic
def submit_condition(user,booking_id,stage,condition,notes='',evidence=None):
    base=get_object_or_404(Booking.objects.select_related('resource'),pk=booking_id)
    resource=Resource.objects.select_for_update().get(pk=base.resource_id)
    booking=Booking.objects.select_for_update().get(pk=booking_id)
    if booking.borrower_id!=user.pk: raise PermissionDenied('Only the borrower can report their condition.')
    membership(user,resource.organisation)
    if stage=='before':
        if booking.status!='approved': raise ValidationError('Handover requires an approved booking.')
        # Allows check-in up to 30 minutes before start and within booking end.
        if timezone.now() < booking.start-timedelta(minutes=30) or timezone.now() > booking.end:
            raise ValidationError('Check-in is only available near your approved booking time.')
        next_status='checkin_pending'
    elif stage=='after':
        if booking.status!='active': raise ValidationError('Only active bookings can be returned.')
        next_status='return_pending'
    else: raise ValidationError('Invalid condition report stage.')
    if ConditionReport.objects.filter(booking=booking,stage=stage).exists():
        raise ValidationError('This condition report has already been submitted.')
    report=ConditionReport.objects.create(booking=booking,stage=stage,condition=condition,
                                           notes=notes,evidence=evidence or '',created_by=user)
    booking.status=next_status
    booking.save(update_fields=['status','updated_at'])
    audit(resource.organisation,user,'condition.'+stage+'_submitted',report,booking_id=booking.pk,condition=condition)
    notify(resource.owner,'Handover action required',f'{resource.name} has a {stage}-use condition report awaiting your confirmation.',booking)
    return report


@transaction.atomic
def confirm_handover(user,booking_id,action):
    base=get_object_or_404(Booking.objects.select_related('resource'),pk=booking_id)
    resource=Resource.objects.select_for_update().get(pk=base.resource_id)
    reviewer(user,resource)
    booking=Booking.objects.select_for_update().get(pk=booking_id)
    if booking.borrower_id==user.pk: raise ValidationError('Independent staff confirmation is required.')
    if action=='checkin':
        expected='checkin_pending'; stage='before'; new='active'
    elif action=='return':
        expected='return_pending'; stage='after'; new='completed'
    else: raise ValidationError('Invalid handover confirmation.')
    if booking.status!=expected: raise ValidationError('The booking is not awaiting this confirmation.')
    report=ConditionReport.objects.select_for_update().get(booking=booking,stage=stage)
    report.verified_by=user
    report.verified_at=timezone.now()
    report.save(update_fields=['verified_by','verified_at','updated_at'])
    booking.status=new
    if action=='checkin': booking.checked_in_at=timezone.now()
    else: booking.completed_at=timezone.now()
    booking.save()
    audit(resource.organisation,user,'handover.'+action+'_confirmed',booking,condition=report.condition)
    notify(booking.borrower,'Handover confirmed',f'{resource.name}: {booking.get_status_display()}.',booking)
    if action=='return':
        if report.condition=='damaged' and not Incident.objects.filter(booking=booking,category='damage').exists():
            incident=Incident.objects.create(booking=booking,reporter=report.created_by,category='damage',
                               description=report.notes or 'Damage was indicated on the final condition report.')
            audit(resource.organisation,user,'incident.flagged_for_review',incident,booking_id=booking.pk)
            notify(resource.owner,'Damage review required','An incident was opened for a return with reported damage.',booking)
        promote_waitlist(resource,booking.start,booking.end)
    return booking


@transaction.atomic
def report_incident(user,booking_id,category,description):
    booking=get_object_or_404(Booking.objects.select_related('resource'),pk=booking_id)
    if booking.borrower_id != user.pk:
        reviewer(user,booking.resource)
    if booking.status in ('requested','waitlisted','rejected'):
        raise ValidationError('Incidents can be reported after a booking is approved.')
    incident=Incident.objects.create(booking=booking,reporter=user,category=category,description=description)
    audit(booking.resource.organisation,user,'incident.reported',incident,booking_id=booking.pk)
    notify(booking.resource.owner,'Incident reported',f'A {category} incident needs review.',booking)
    return incident


@transaction.atomic
def resolve_incident(user,incident_id,outcome):
    incident=get_object_or_404(Incident.objects.select_related('booking__resource').select_for_update(),pk=incident_id)
    reviewer(user,incident.booking.resource)
    if incident.status=='resolved': raise ValidationError('This incident is already resolved.')
    if len(outcome.strip())<10: raise ValidationError('Provide a meaningful resolution explanation.')
    incident.status='resolved'; incident.outcome=outcome.strip()
    incident.resolved_by=user; incident.resolved_at=timezone.now(); incident.save()
    audit(incident.booking.resource.organisation,user,'incident.resolved',incident,outcome=incident.outcome[:300])
    notify(incident.booking.borrower,'Incident review complete',incident.outcome[:200],incident.booking)
    return incident
