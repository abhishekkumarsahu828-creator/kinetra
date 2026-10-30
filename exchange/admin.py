"""Emergency platform admin. Operational changes MUST pass through audited app workflows."""
from django.contrib import admin
from .models import (Organisation,Membership,Credential,Resource,Blackout,Booking,ConditionReport,
                     Incident,Notification,AuditEvent,TrainingAttempt)

class OperationalReadOnly(admin.ModelAdmin):
    """Superadmin may inspect but not bypass domain services via admin forms."""
    def has_add_permission(self,request): return False
    def has_change_permission(self,request,obj=None): return False
    def has_delete_permission(self,request,obj=None): return False

@admin.register(Organisation)
class OrganisationAdmin(OperationalReadOnly):
    list_display=('name','slug','city','is_active')
    search_fields=('name','city')

@admin.register(Membership)
class MembershipAdmin(OperationalReadOnly):
    list_display=('user','organisation','role','status')
    list_filter=('role','status','organisation')

@admin.register(Credential)
class CredentialAdmin(OperationalReadOnly):
    list_display=('title','member','status','expires_at')
    list_filter=('status',)

@admin.register(TrainingAttempt)
class TrainingAttemptAdmin(OperationalReadOnly):
    list_display=('training_title','membership','resource','score','passed','completed_at')
    list_filter=('passed','training_title')

@admin.register(Resource)
class ResourceAdmin(OperationalReadOnly):
    list_display=('name','organisation','category','owner','status')
    list_filter=('status','category','organisation')
    search_fields=('name','location','summary')

@admin.register(Booking)
class BookingAdmin(OperationalReadOnly):
    list_display=('public_id','resource','borrower','start','end','status')
    list_filter=('status','resource__organisation')

@admin.register(AuditEvent)
class AuditAdmin(OperationalReadOnly):
    list_display=('created_at','actor','verb','organisation','object_type','object_id')
    list_filter=('organisation','verb')

@admin.register(Incident)
class IncidentAdmin(OperationalReadOnly):
    list_display=('id','booking','category','status','reporter')

@admin.register(Blackout)
class BlackoutAdmin(OperationalReadOnly): pass

@admin.register(ConditionReport)
class ConditionReportAdmin(OperationalReadOnly): pass

@admin.register(Notification)
class NotificationAdmin(OperationalReadOnly): pass
