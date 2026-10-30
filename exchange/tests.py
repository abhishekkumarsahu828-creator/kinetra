"""Core regression suite. Run using `python manage.py test exchange`."""
from datetime import datetime,timedelta,time
from unittest.mock import patch
from django.test import TestCase,Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied,ValidationError
from django.utils import timezone
from .models import Organisation,Membership,Credential,Resource,Booking,ConditionReport,Incident,AuditEvent,Notification
from . import services

class SharingJourneyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User=get_user_model()
        cls.admin=User.objects.create_user('admin_test',password='StrongPassword.987')
        cls.owner=User.objects.create_user('owner_test',password='StrongPassword.987')
        cls.student=User.objects.create_user('student_test',password='StrongPassword.987')
        cls.other=User.objects.create_user('other_test',password='StrongPassword.987')
        cls.outsider=User.objects.create_user('outsider_test',password='StrongPassword.987')
        cls.org=Organisation.objects.create(name='Fictional North Campus',slug='fictional-north')
        for user,role in [(cls.admin,'admin'),(cls.owner,'owner'),(cls.student,'member'),(cls.other,'member')]:
            Membership.objects.create(user=user,organisation=cls.org,role=role,status='active')
        cls.resource=Resource.objects.create(organisation=cls.org,owner=cls.owner,name='3D Printer',category='fabrication',
            summary='Fictional campus fabrication machine',description='Test equipment',location='Lab 2',
            available_days='0,1,2,3,4,5,6',open_time=time(0,0),close_time=time(23,59),
            max_hours=4,required_training='3D Printer Safety')
        Credential.objects.create(member=Membership.objects.get(user=cls.student,organisation=cls.org),
            title='3D Printer Safety',status='verified',reviewed_by=cls.admin)
        Credential.objects.create(member=Membership.objects.get(user=cls.other,organisation=cls.org),
            title='3D Printer Safety',status='verified',reviewed_by=cls.admin)

    def setUp(self):
        base=timezone.localtime(timezone.now())+timedelta(days=2)
        self.start=timezone.make_aware(datetime.combine(base.date(),time(11,0)),timezone.get_current_timezone())
        self.end=self.start+timedelta(hours=2)

    def request(self,user=None):
        return services.request_booking(user or self.student,self.resource.pk,self.start,self.end,'Student coursework prototype')

    def test_full_resource_lifecycle_with_audit(self):
        booking=self.request()
        self.assertEqual(booking.status,'requested')
        services.decide_booking(self.owner,booking.pk,'approve')
        booking.refresh_from_db(); self.assertEqual(booking.status,'approved')
        with patch('exchange.services.timezone.now',return_value=self.start):
            services.submit_condition(self.student,booking.pk,'before','good','All accessories present')
        booking.refresh_from_db();self.assertEqual(booking.status,'checkin_pending')
        services.confirm_handover(self.owner,booking.pk,'checkin')
        services.submit_condition(self.student,booking.pk,'after','good','Clean return')
        services.confirm_handover(self.owner,booking.pk,'return')
        booking.refresh_from_db();self.assertEqual(booking.status,'completed')
        self.assertEqual(ConditionReport.objects.filter(booking=booking).count(),2)
        self.assertGreaterEqual(AuditEvent.objects.filter(organisation=self.org).count(),6)
        self.assertTrue(Notification.objects.filter(user=self.student).exists())

    def test_unverified_user_cannot_request(self):
        with self.assertRaises(ValidationError):
            self.request(self.outsider)
        member=Membership.objects.get(user=self.other,organisation=self.org)
        member.status='pending';member.save()
        with self.assertRaises(ValidationError):
            self.request(self.other)

    def test_waitlist_and_fair_human_promotion(self):
        first=self.request()
        services.decide_booking(self.owner,first.pk,'approve')
        second=self.request(self.other)
        self.assertEqual(second.status,'waitlisted')
        with self.assertRaises(ValidationError):
            services.decide_booking(self.owner,second.pk,'approve')
        services.cancel_booking(self.student,first.pk)
        second.refresh_from_db()
        self.assertEqual(second.status,'requested')  # Not automatically approved.
        services.decide_booking(self.owner,second.pk,'approve')
        second.refresh_from_db(); self.assertEqual(second.status,'approved')

    def test_no_conflicting_confirmed_slots(self):
        first=self.request()
        services.decide_booking(self.owner,first.pk,'approve')
        second=self.request(self.other)
        self.assertTrue(services.active_conflicts(self.resource,self.start,self.end,exclude=second.pk))
        self.assertEqual(second.status,'waitlisted')

    def test_cannot_self_approve(self):
        booking=self.request()
        with self.assertRaises(PermissionDenied):
            services.decide_booking(self.student,booking.pk,'approve')

    def test_independent_handover_confirmation(self):
        booking=self.request();services.decide_booking(self.owner,booking.pk,'approve')
        with patch('exchange.services.timezone.now',return_value=self.start):
            services.submit_condition(self.student,booking.pk,'before','good')
        with self.assertRaises(PermissionDenied):
            services.confirm_handover(self.student,booking.pk,'checkin')
        services.confirm_handover(self.owner,booking.pk,'checkin')
        booking.refresh_from_db();self.assertEqual(booking.status,'active')

    def test_damaged_return_flags_incident_for_human_review(self):
        booking=self.request();services.decide_booking(self.owner,booking.pk,'approve')
        with patch('exchange.services.timezone.now',return_value=self.start):
            services.submit_condition(self.student,booking.pk,'before','good')
        services.confirm_handover(self.owner,booking.pk,'checkin')
        services.submit_condition(self.student,booking.pk,'after','damaged','Visible cracked casing')
        services.confirm_handover(self.owner,booking.pk,'return')
        incident=Incident.objects.get(booking=booking)
        self.assertEqual(incident.status,'open')
        services.resolve_incident(self.owner,incident.pk,'Reviewed by owner; repair inspection is scheduled.')
        incident.refresh_from_db();self.assertEqual(incident.status,'resolved')

    def test_double_submission_rejected(self):
        self.request()
        with self.assertRaises(ValidationError):self.request()

    def test_resource_owner_permissions(self):
        with self.assertRaises(PermissionDenied):services.reviewer(self.student,self.resource)
        self.assertIsNotNone(services.reviewer(self.owner,self.resource))
        other_org=Organisation.objects.create(name='Other campus',slug='other-campus')
        Membership.objects.create(user=self.student,organisation=other_org,status='active',role='owner')
        with self.assertRaises(PermissionDenied):services.reviewer(self.student,self.resource)

    def test_booking_visibility_by_role(self):
        booking=self.request()
        c=Client()
        c.force_login(self.outsider)
        r=c.get(reverse('booking_detail',args=[booking.pk]))
        self.assertEqual(r.status_code,403)
        c.force_login(self.student)
        self.assertEqual(c.get(reverse('booking_detail',args=[booking.pk])).status_code,200)
        c.force_login(self.owner)
        self.assertEqual(c.get(reverse('booking_detail',args=[booking.pk])).status_code,200)

    def test_get_cannot_change_booking(self):
        b=self.request()
        c=Client();c.force_login(self.owner)
        self.assertEqual(c.get(reverse('booking_decision',args=[b.pk])).status_code,405)
        b.refresh_from_db();self.assertEqual(b.status,'requested')

    def test_public_resource_marketplace_and_search(self):
        response=self.client.get(reverse('marketplace'),{'q':'3D Printer'})
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'3D Printer')

    def test_fair_access_limit(self):
        self.resource.max_hours=4;self.resource.save()
        self.request()
        other_start=self.start+timedelta(hours=4)
        services.request_booking(self.student,self.resource.pk,other_start,other_start+timedelta(hours=2),'Second project')
        later=self.start+timedelta(hours=8)
        with self.assertRaises(ValidationError):
            services.request_booking(self.student,self.resource.pk,later,later+timedelta(hours=2),'Third project')
