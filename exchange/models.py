import uuid
from datetime import timedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, F
from django.utils import timezone


def public_id():
    return uuid.uuid4().hex[:12].upper()

class TimeStamped(models.Model):
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        abstract=True

class Organisation(TimeStamped):
    name=models.CharField(max_length=150)
    slug=models.SlugField(unique=True)
    description=models.TextField(blank=True)
    city=models.CharField(max_length=120,blank=True)
    contact_email=models.EmailField(blank=True)
    is_active=models.BooleanField(default=True)
    max_active_bookings=models.PositiveSmallIntegerField(default=2)
    fair_usage_days=models.PositiveSmallIntegerField(default=30)
    def __str__(self): return self.name

class Membership(TimeStamped):
    class Role(models.TextChoices):
        MEMBER='member','Borrower'
        OWNER='owner','Resource owner'
        MANAGER='manager','Manager'
        ADMIN='admin','Organisation admin'
    class Status(models.TextChoices):
        PENDING='pending','Pending verification'
        ACTIVE='active','Verified'
        REJECTED='rejected','Rejected'
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='memberships')
    organisation=models.ForeignKey(Organisation,on_delete=models.CASCADE,related_name='memberships')
    role=models.CharField(max_length=12,choices=Role.choices,default=Role.MEMBER)
    status=models.CharField(max_length=12,choices=Status.choices,default=Status.PENDING)
    reviewed_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='+')
    class Meta:
        constraints=[models.UniqueConstraint(fields=['user','organisation'],name='unique_org_membership')]
    def __str__(self): return f'{self.user.username} · {self.organisation.name} · {self.role}'

class Credential(TimeStamped):
    class Status(models.TextChoices):
        PENDING='pending','Pending'
        VERIFIED='verified','Verified'
        REJECTED='rejected','Rejected'
    member=models.ForeignKey(Membership,on_delete=models.CASCADE,related_name='credentials')
    title=models.CharField(max_length=150)
    status=models.CharField(max_length=12,choices=Status.choices,default=Status.PENDING)
    expires_at=models.DateField(null=True,blank=True)
    reviewed_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='+')
    review_note=models.CharField(max_length=300,blank=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['member','title'],name='unique_credential_per_member')]
    def __str__(self): return f'{self.title} ({self.member.user.username})'

class Resource(TimeStamped):
    class Category(models.TextChoices):
        LAB='lab','Laboratory'
        SPACE='space','Meeting & study spaces'
        PRINT='fabrication','Fabrication'
        MEDIA='media','Media equipment'
        COMPUTING='computing','Computing'
        TOOLS='tools','Tools & electronics'
    class Status(models.TextChoices):
        ACTIVE='active','Available for requests'
        MAINTENANCE='maintenance','Under maintenance'
        ARCHIVED='archived','Archived'
    public_id=models.CharField(max_length=12,unique=True,default=public_id,editable=False)
    organisation=models.ForeignKey(Organisation,on_delete=models.PROTECT,related_name='resources')
    owner=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='owned_resources')
    name=models.CharField(max_length=160)
    category=models.CharField(max_length=18,choices=Category.choices)
    summary=models.CharField(max_length=230)
    description=models.TextField()
    location=models.CharField(max_length=180)
    equipment_specs=models.TextField(blank=True)
    usage_rules=models.TextField(blank=True)
    required_training=models.CharField(max_length=150,blank=True)
    requires_supervision=models.BooleanField(default=False)
    max_hours=models.PositiveSmallIntegerField(default=4)
    weekly_hours_limit=models.PositiveSmallIntegerField(default=10)
    advance_booking_days=models.PositiveSmallIntegerField(default=30)
    open_time=models.TimeField(default='08:00')
    close_time=models.TimeField(default='20:00')
    available_days=models.CharField(max_length=40,default='0,1,2,3,4,5')  # Mon=0
    image=models.ImageField(upload_to='resource_images/%Y/%m/',blank=True)
    status=models.CharField(max_length=12,choices=Status.choices,default=Status.ACTIVE)
    class Meta:
        indexes=[models.Index(fields=['organisation','category','status'],name='res_org_cat_status_idx'),models.Index(fields=['name'],name='res_name_idx')]
        ordering=['-created_at']
    def __str__(self): return self.name
    def clean(self):
        if self.close_time and self.open_time and self.open_time>=self.close_time:
            raise ValidationError('Closing time must be after opening time.')
        if self.max_hours < 1: raise ValidationError('Maximum booking duration must be positive.')

class Blackout(TimeStamped):
    resource=models.ForeignKey(Resource,on_delete=models.CASCADE,related_name='blackouts')
    start=models.DateTimeField()
    end=models.DateTimeField()
    reason=models.CharField(max_length=200)
    class Meta:
        constraints=[models.CheckConstraint(condition=Q(end__gt=F('start')),name='blackout_end_after_start')]

class Booking(TimeStamped):
    class Status(models.TextChoices):
        REQUESTED='requested','Awaiting review'
        WAITLISTED='waitlisted','Waitlisted'
        APPROVED='approved','Approved'
        REJECTED='rejected','Declined'
        CANCELLED='cancelled','Cancelled'
        CHECKIN_PENDING='checkin_pending','Handover review'
        ACTIVE='active','In use'
        RETURN_PENDING='return_pending','Return review'
        COMPLETED='completed','Completed'
    public_id=models.CharField(max_length=12,unique=True,default=public_id,editable=False)
    resource=models.ForeignKey(Resource,on_delete=models.PROTECT,related_name='bookings')
    borrower=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='bookings')
    start=models.DateTimeField()
    end=models.DateTimeField()
    purpose=models.TextField(max_length=600)
    status=models.CharField(max_length=18,choices=Status.choices,default=Status.REQUESTED)
    decision_reason=models.TextField(blank=True)
    reviewed_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='reviewed_bookings')
    reviewed_at=models.DateTimeField(null=True,blank=True)
    checked_in_at=models.DateTimeField(null=True,blank=True)
    completed_at=models.DateTimeField(null=True,blank=True)
    class Meta:
        indexes=[models.Index(fields=['resource','status','start','end'],name='book_res_status_time_idx'),models.Index(fields=['borrower','status'],name='book_borrower_status_idx')]
        constraints=[models.CheckConstraint(condition=Q(end__gt=F('start')),name='booking_end_after_start')]
        ordering=['-created_at']
    def __str__(self): return f'{self.resource.name} · {self.borrower.username} · {self.status}'
    @property
    def hours(self): return (self.end-self.start).total_seconds()/3600
    @property
    def is_overdue(self): return self.status in ('active','return_pending') and self.end < timezone.now()

class ConditionReport(TimeStamped):
    class Stage(models.TextChoices):
        BEFORE='before','Before use'
        AFTER='after','After use'
    booking=models.ForeignKey(Booking,on_delete=models.PROTECT,related_name='condition_reports')
    stage=models.CharField(max_length=8,choices=Stage.choices)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    condition=models.CharField(max_length=20,choices=[('excellent','Excellent'),('good','Good'),('fair','Wear observed'),('damaged','Damage observed')])
    notes=models.TextField(blank=True)
    evidence=models.ImageField(upload_to='condition_evidence/%Y/%m/',blank=True)
    verified_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='+')
    verified_at=models.DateTimeField(null=True,blank=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['booking','stage'],name='one_condition_report_per_stage')]

class Incident(TimeStamped):
    class Status(models.TextChoices):
        OPEN='open','Open'
        REVIEW='review','Under review'
        RESOLVED='resolved','Resolved'
    booking=models.ForeignKey(Booking,on_delete=models.PROTECT,related_name='incidents')
    reporter=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='reported_incidents')
    category=models.CharField(max_length=20,choices=[('damage','Damage'),('delay','Late return'),('conflict','Scheduling conflict'),('malfunction','Malfunction'),('safety','Safety issue'),('other','Other')])
    description=models.TextField(max_length=1500)
    status=models.CharField(max_length=10,choices=Status.choices,default=Status.OPEN)
    outcome=models.TextField(blank=True)
    resolved_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='+')
    resolved_at=models.DateTimeField(null=True,blank=True)
    def __str__(self): return f'Incident #{self.pk}: {self.get_category_display()}'

class Notification(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='notifications')
    title=models.CharField(max_length=150)
    body=models.CharField(max_length=500)
    link=models.CharField(max_length=250,blank=True)
    read_at=models.DateTimeField(null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=['-created_at']

class AuditEvent(models.Model):
    organisation=models.ForeignKey(Organisation,on_delete=models.PROTECT,related_name='events')
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='+')
    verb=models.CharField(max_length=60)
    object_type=models.CharField(max_length=40)
    object_id=models.PositiveBigIntegerField()
    details=models.JSONField(default=dict)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=['-created_at']
        indexes=[models.Index(fields=['organisation','created_at'],name='audit_org_created_idx')]
