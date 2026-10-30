"""Views compose domain services; authorization must not be implemented in templates."""
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q, Count
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404,redirect,render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from . import services
from .forms import SignupForm,ResourceForm,BookingForm,ConditionForm,IncidentForm,CredentialForm,BlackoutForm
from .models import (Organisation,Membership,Credential,Resource,Booking,ConditionReport,Blackout,
                     Incident,Notification,AuditEvent)


def _fail(request,e):
    if isinstance(e,ValidationError):
        for m in e.messages: messages.error(request,m)
    else: messages.error(request,str(e))


def home(request):
    active_resources=Resource.objects.filter(status='active',organisation__is_active=True).select_related('organisation')
    featured=active_resources[:6]
    return render(request,'exchange/home.html',{'featured':featured,'hero_resource':active_resources.first(),
        'resource_count':active_resources.count(),
        'org_count':Organisation.objects.filter(is_active=True).count()})


def marketplace(request):
    qs=Resource.objects.filter(status='active',organisation__is_active=True).select_related('organisation','owner')
    query=request.GET.get('q','').strip()[:100]
    category=request.GET.get('category','')
    organisation=request.GET.get('organisation','')
    training=request.GET.get('training','')
    if query: qs=qs.filter(Q(name__icontains=query)|Q(summary__icontains=query)|Q(description__icontains=query)|Q(location__icontains=query))
    if category in Resource.Category.values: qs=qs.filter(category=category)
    if organisation.isdigit(): qs=qs.filter(organisation_id=int(organisation))
    if training=='none': qs=qs.filter(required_training='')
    from django.core.paginator import Paginator
    results=Paginator(qs,9).get_page(request.GET.get('page'))
    return render(request,'exchange/marketplace.html',{'page_obj':results,'q':query,'category':category,
         'organisation':organisation,'training':training,'categories':Resource.Category.choices,
         'organisations':Organisation.objects.filter(is_active=True).order_by('name')})


def resource_detail(request,pk):
    resource=get_object_or_404(Resource.objects.filter(organisation__is_active=True).select_related('organisation','owner'),pk=pk)
    if resource.status=='archived': raise Http404()
    eligible,eligibility_message=(False,'Sign in to check your eligibility.')
    if request.user.is_authenticated:
        eligible,eligibility_message=services.credential_status(request.user,resource)
    bookings=Booking.objects.filter(resource=resource,status__in=services.BLOCKING,start__gte=timezone.now()-timedelta(days=1)).order_by('start')[:12]
    return render(request,'exchange/resource_detail.html',{'resource':resource,'eligible':eligible,
       'eligibility_message':eligibility_message,'reserved':bookings})


def register(request):
    if request.user.is_authenticated: return redirect('dashboard')
    form=SignupForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            user=form.save(commit=False)
            user.email=form.cleaned_data['email']; user.first_name=form.cleaned_data['first_name']; user.last_name=form.cleaned_data['last_name']
            user.save()
            org=form.cleaned_data['organisation']
            m=Membership.objects.create(user=user,organisation=org,role='member',status='pending')
            services.audit(org,user,'membership.requested',m)
        login(request,user)
        messages.success(request,'Account created. Your institutional membership is awaiting administrator verification.')
        return redirect('dashboard')
    return render(request,'accounts/register.html',{'form':form})


@login_required
def dashboard(request):
    memberships=Membership.objects.filter(user=request.user).select_related('organisation').order_by('-created_at')
    bookings=Booking.objects.filter(borrower=request.user).select_related('resource','resource__organisation')[:8]
    owned=Resource.objects.filter(owner=request.user).exclude(status='archived')[:5]
    incoming=Booking.objects.filter(resource__owner=request.user,status__in=['requested','checkin_pending','return_pending']).select_related('resource','borrower')[:8]
    stats={'upcoming':Booking.objects.filter(borrower=request.user,status='approved').count(),
           'in_use':Booking.objects.filter(borrower=request.user,status__in=['active','return_pending']).count(),
           'waiting':Booking.objects.filter(borrower=request.user,status__in=['requested','waitlisted']).count(),
           'completed':Booking.objects.filter(borrower=request.user,status='completed').count()}
    return render(request,'exchange/dashboard.html',{'memberships':memberships,'bookings':bookings,'owned':owned,
          'incoming':incoming,'stats':stats})


@login_required
def booking_create(request,pk):
    resource=get_object_or_404(Resource,pk=pk,status='active')
    services.membership(request.user,resource.organisation)
    eligible,message=services.credential_status(request.user,resource)
    if not eligible:
        messages.warning(request,message)
        return redirect('resource_detail',pk=pk)
    form=BookingForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        try:
            booking=services.request_booking(request.user,resource.pk,
               form.cleaned_data['start'],form.cleaned_data['end'],form.cleaned_data['purpose'])
            messages.success(request,'Request submitted. '+ ('You are on the waiting list.' if booking.status=='waitlisted' else 'The owner will review it.'))
            return redirect('booking_detail',pk=booking.pk)
        except ValidationError as e: _fail(request,e)
    return render(request,'exchange/form.html',{'page_title':'Request access','eyebrow':'RESOURCE BOOKING',
       'description':f'Select an available time for {resource.name}. Approval is required before use.',
       'form':form,'submit_label':'Submit booking request','back_url':reverse('resource_detail',args=[pk])})


@login_required
def my_bookings(request):
    from django.core.paginator import Paginator
    qs=Booking.objects.filter(borrower=request.user).select_related('resource','resource__organisation')
    status=request.GET.get('status','')
    if status in Booking.Status.values: qs=qs.filter(status=status)
    page=Paginator(qs,20).get_page(request.GET.get('page'))
    return render(request,'exchange/my_bookings.html',{'page_obj':page,'status_filter':status,
        'statuses':Booking.Status.choices})


@login_required
def booking_detail(request,pk):
    booking=get_object_or_404(Booking.objects.select_related('resource','resource__organisation','borrower','reviewed_by'),pk=pk)
    is_borrower=booking.borrower_id==request.user.pk
    can_review=False
    try: services.reviewer(request.user,booking.resource); can_review=True
    except PermissionDenied: pass
    if not is_borrower and not can_review: raise PermissionDenied()
    reports=booking.condition_reports.select_related('created_by','verified_by')
    incidents=booking.incidents.select_related('reporter','resolved_by')
    audit=AuditEvent.objects.filter(organisation=booking.resource.organisation,
       object_type='Booking',object_id=booking.pk)
    # Also include reports/incidents associated with this booking, not unrelated organisation events.
    timeline=list(audit)
    report_ids=list(reports.values_list('id',flat=True))
    incident_ids=list(incidents.values_list('id',flat=True))
    timeline += list(AuditEvent.objects.filter(organisation=booking.resource.organisation,object_type='ConditionReport',object_id__in=report_ids))
    timeline += list(AuditEvent.objects.filter(organisation=booking.resource.organisation,object_type='Incident',object_id__in=incident_ids))
    timeline.sort(key=lambda e:e.created_at)
    return render(request,'exchange/booking_detail.html',{'booking':booking,'is_borrower':is_borrower,
       'can_review':can_review,'reports':reports,'incidents':incidents,'timeline':timeline})


@login_required
@require_POST
def booking_decision(request,pk):
    action=request.POST.get('action','')
    try:
        services.decide_booking(request.user,pk,action,request.POST.get('reason',''))
        messages.success(request,'Decision saved and recorded in the audit history.')
    except (ValidationError,PermissionDenied) as e: _fail(request,e)
    return redirect('booking_detail',pk=pk)


@login_required
@require_POST
def booking_cancel(request,pk):
    try:
        services.cancel_booking(request.user,pk,request.POST.get('reason',''))
        messages.success(request,'Booking cancelled. Any eligible waiting-list candidates will be reviewed.')
    except (ValidationError,PermissionDenied) as e: _fail(request,e)
    return redirect('booking_detail',pk=pk)


@login_required
def condition_submit(request,pk,stage):
    booking=get_object_or_404(Booking.objects.select_related('resource'),pk=pk)
    if booking.borrower_id!=request.user.pk: raise PermissionDenied()
    if stage not in ('before','after'): raise Http404()
    form=ConditionForm(request.POST or None,request.FILES or None)
    if request.method=='POST' and form.is_valid():
        try:
            services.submit_condition(request.user,pk,stage,form.cleaned_data['condition'],
              form.cleaned_data.get('notes',''),form.cleaned_data.get('evidence'))
            messages.success(request,'Condition recorded. An authorised owner must confirm the handover.')
            return redirect('booking_detail',pk=pk)
        except ValidationError as e: _fail(request,e)
    return render(request,'exchange/form.html',{'page_title':'Before-use condition' if stage=='before' else 'Return condition',
       'eyebrow':'RESOURCE ACCOUNTABILITY','description':'Document the resource accurately. Your report is visible to authorised participants.',
       'form':form,'submit_label':'Submit condition report','back_url':reverse('booking_detail',args=[pk]),'has_files':True})


@login_required
@require_POST
def handover_confirm(request,pk,action):
    try:
        services.confirm_handover(request.user,pk,action)
        messages.success(request,'Handover confirmed and audited.')
    except (PermissionDenied,ValidationError,ConditionReport.DoesNotExist) as e: _fail(request,e)
    return redirect('booking_detail',pk=pk)


@login_required
def incident_create(request,pk):
    booking=get_object_or_404(Booking.objects.select_related('resource'),pk=pk)
    if booking.borrower_id!=request.user.pk: services.reviewer(request.user,booking.resource)
    form=IncidentForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        try:
            services.report_incident(request.user,pk,form.cleaned_data['category'],form.cleaned_data['description'])
            messages.success(request,'Incident submitted for human review.')
            return redirect('booking_detail',pk=pk)
        except ValidationError as e: _fail(request,e)
    return render(request,'exchange/form.html',{'page_title':'Report an incident','eyebrow':'TRUST & SAFETY',
       'description':'Describe what happened. Reports are reviewed by authorised personnel.',
       'form':form,'submit_label':'Submit incident','back_url':reverse('booking_detail',args=[pk])})


@login_required
@require_POST
def incident_resolve(request,pk):
    incident=get_object_or_404(Incident,pk=pk)
    try:
        services.resolve_incident(request.user,pk,request.POST.get('outcome',''))
        messages.success(request,'Incident resolution recorded.')
    except (ValidationError,PermissionDenied) as e: _fail(request,e)
    return redirect('booking_detail',pk=incident.booking_id)


def _can_manage(user,resource):
    services.reviewer(user,resource)
    return True


@login_required
def resource_create(request):
    org_id=request.GET.get('org') or request.POST.get('org')
    org=get_object_or_404(Organisation,pk=org_id) if str(org_id).isdigit() else None
    allowed=Membership.objects.filter(user=request.user,status='active',role__in=['owner','manager','admin']).select_related('organisation')
    if org is None:
        return render(request,'exchange/select_org.html',{'memberships':allowed})
    services.membership(request.user,org,services.REVIEWER_ROLES)
    form=ResourceForm(request.POST or None,request.FILES or None)
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            resource=form.save(commit=False); resource.owner=request.user; resource.organisation=org
            resource.full_clean(); resource.save()
            services.audit(org,request.user,'resource.created',resource)
        messages.success(request,'Resource published successfully.')
        return redirect('resource_detail',pk=resource.pk)
    return render(request,'exchange/form.html',{'page_title':'List a resource','eyebrow':org.name.upper(),
          'description':'Publish equipment or space with availability, safety rules and clear eligibility.',
          'form':form,'has_files':True,'submit_label':'Publish resource','back_url':reverse('dashboard'),'extra_hidden':{'org':org.pk}})


@login_required
def resource_edit(request,pk):
    resource=get_object_or_404(Resource,pk=pk)
    _can_manage(request.user,resource)
    form=ResourceForm(request.POST or None,request.FILES or None,instance=resource)
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            obj=form.save(commit=False); obj.full_clean(); obj.save()
            services.audit(resource.organisation,request.user,'resource.updated',obj)
        messages.success(request,'Resource updated.')
        return redirect('resource_detail',pk=pk) if resource.status!='archived' else redirect('dashboard')
    return render(request,'exchange/form.html',{'page_title':'Edit resource','eyebrow':'RESOURCE MANAGEMENT',
          'description':'Update policy or availability carefully. Approved bookings retain their commitments.',
          'form':form,'has_files':True,'submit_label':'Save changes','back_url':reverse('resource_detail',args=[pk])})


@login_required
def blackout_create(request,pk):
    resource=get_object_or_404(Resource,pk=pk)
    _can_manage(request.user,resource)
    form=BlackoutForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        start=form.cleaned_data['start']; end=form.cleaned_data['end']
        with transaction.atomic():
            Resource.objects.select_for_update().get(pk=resource.pk)
            if Booking.objects.filter(resource=resource,status__in=services.BLOCKING,start__lt=end,end__gt=start).exists():
                messages.error(request,'This period conflicts with an approved booking. Resolve the booking first.')
            else:
                block=form.save(commit=False); block.resource=resource; block.save()
                services.audit(resource.organisation,request.user,'resource.blackout_added',block,resource_id=pk)
                messages.success(request,'Maintenance block saved.')
                return redirect('resource_detail',pk=pk)
    return render(request,'exchange/form.html',{'page_title':'Block availability','eyebrow':'MAINTENANCE',
          'description':'Prevent booking during maintenance or institutional closures.',
          'form':form,'submit_label':'Block these dates','back_url':reverse('resource_detail',args=[pk])})


@login_required
def owner_queue(request):
    org_ids=list(Membership.objects.filter(user=request.user,status='active',role__in=['manager','admin']).values_list('organisation_id',flat=True))
    qs=Booking.objects.filter(Q(resource__owner=request.user)|Q(resource__organisation_id__in=org_ids),
      status__in=['requested','waitlisted','checkin_pending','return_pending']).select_related('resource','borrower','resource__organisation').distinct().order_by('created_at')[:100]
    incidents=Incident.objects.filter(Q(booking__resource__owner=request.user)|Q(booking__resource__organisation_id__in=org_ids),
        status__in=['open','review']).select_related('booking__resource')[:30]
    return render(request,'exchange/owner_queue.html',{'queue':qs,'incidents':incidents})


@login_required
def membership_manage(request,org_pk):
    org=get_object_or_404(Organisation,pk=org_pk)
    services.membership(request.user,org,{'admin','manager'})
    members=Membership.objects.filter(organisation=org).select_related('user').order_by('status','-created_at')
    credentials=Credential.objects.filter(member__organisation=org).select_related('member__user').order_by('status','-created_at')[:100]
    return render(request,'exchange/membership_manage.html',{'organisation':org,'members':members,'credentials':credentials})


@login_required
@require_POST
def membership_review(request,pk):
    item=get_object_or_404(Membership.objects.select_related('organisation'),pk=pk)
    admin_member=services.membership(request.user,item.organisation,{'admin','manager'})
    if item.user_id==request.user.pk: raise PermissionDenied('Self-review is forbidden.')
    decision=request.POST.get('decision')
    role=request.POST.get('role','member')
    if decision not in ('active','rejected') or role not in Membership.Role.values:
        messages.error(request,'Invalid decision or role.')
        return redirect('membership_manage',org_pk=item.organisation_id)
    if admin_member.role!='admin' and (role in ('admin','manager','owner') or item.role in ('admin','manager','owner')):
        raise PermissionDenied('Only organisation admins can grant elevated roles.')
    with transaction.atomic():
        item.status=decision; item.role=role; item.reviewed_by=request.user; item.save()
        services.audit(item.organisation,request.user,'membership.reviewed',item,decision=decision,role=role)
        services.notify(item.user,'Membership '+('verified' if decision=='active' else 'declined'),f'Your membership at {item.organisation.name} has been reviewed.')
    messages.success(request,'Membership decision saved.')
    return redirect('membership_manage',org_pk=item.organisation_id)


@login_required
def credential_request(request,org_pk):
    org=get_object_or_404(Organisation,pk=org_pk)
    member=services.membership(request.user,org)
    form=CredentialForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        title=form.cleaned_data['title'].strip()
        if Credential.objects.filter(member=member,title__iexact=title).exists():
            messages.error(request,'A credential with this title is already recorded.')
        else:
            cred=Credential.objects.create(member=member,title=title)
            services.audit(org,request.user,'credential.requested',cred)
            messages.success(request,'Training verification requested. An authorised reviewer must verify it.')
            return redirect('dashboard')
    return render(request,'exchange/form.html',{'page_title':'Request qualification verification','eyebrow':'ELIGIBILITY',
        'description':'Enter the exact training name shown on the resource. Contact an institutional verifier to confirm your qualification.',
        'form':form,'submit_label':'Request review','back_url':reverse('dashboard')})


@login_required
@require_POST
def credential_review(request,pk):
    cred=get_object_or_404(Credential.objects.select_related('member__organisation'),pk=pk)
    services.membership(request.user,cred.member.organisation,{'manager','admin'})
    if cred.member.user_id==request.user.pk: raise PermissionDenied('You cannot verify your own qualification.')
    decision=request.POST.get('decision')
    if decision not in ('verified','rejected'):
        messages.error(request,'Invalid verification decision.')
        return redirect('membership_manage',org_pk=cred.member.organisation_id)
    with transaction.atomic():
        cred.status=decision; cred.reviewed_by=request.user; cred.review_note=request.POST.get('note','')[:300]
        cred.save()
        services.audit(cred.member.organisation,request.user,'credential.reviewed',cred,decision=decision)
        services.notify(cred.member.user,'Qualification reviewed',f'{cred.title}: {decision}.')
    messages.success(request,'Credential review saved.')
    return redirect('membership_manage',org_pk=cred.member.organisation_id)


@login_required
def notifications(request):
    items=Notification.objects.filter(user=request.user)[:100]
    return render(request,'exchange/notifications.html',{'notifications':items})


@login_required
@require_POST
def notifications_read(request):
    Notification.objects.filter(user=request.user,read_at__isnull=True).update(read_at=timezone.now())
    return redirect('notifications')


@login_required
def activity(request,org_pk):
    org=get_object_or_404(Organisation,pk=org_pk)
    services.membership(request.user,org,{'manager','admin'})
    from django.core.paginator import Paginator
    events=Paginator(AuditEvent.objects.filter(organisation=org).select_related('actor'),30).get_page(request.GET.get('page'))
    return render(request,'exchange/activity.html',{'organisation':org,'page_obj':events})


def resource_photo(request,pk):
    res=get_object_or_404(Resource,pk=pk)
    if not res.image: raise Http404()
    return FileResponse(res.image.open('rb'),content_type=_file_content_type(res.image.name))


def _file_content_type(path):
    path=path.lower()
    return 'image/png' if path.endswith('.png') else 'image/webp' if path.endswith('.webp') else 'image/jpeg'


@login_required
def private_evidence(request,pk):
    report=get_object_or_404(ConditionReport.objects.select_related('booking__resource'),pk=pk)
    booking=report.booking
    if booking.borrower_id!=request.user.pk: services.reviewer(request.user,booking.resource)
    if not report.evidence: raise Http404()
    response=FileResponse(report.evidence.open('rb'),content_type=_file_content_type(report.evidence.name))
    response['Cache-Control']='private, no-store'
    response['X-Content-Type-Options']='nosniff'
    return response


def privacy(request):
    return render(request,'exchange/privacy.html')


def terms(request):
    return render(request,'exchange/terms.html')


def health(request):
    from django.db import connection
    try:
        with connection.cursor() as c: c.execute('SELECT 1')
        return HttpResponse('ok',content_type='text/plain')
    except Exception:
        return HttpResponse('unavailable',status=503,content_type='text/plain')
