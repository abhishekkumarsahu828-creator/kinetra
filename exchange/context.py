from .models import Membership,Notification

def site_context(request):
    if not request.user.is_authenticated:
        return {'nav_memberships':[],'unread_count':0}
    return {'nav_memberships':Membership.objects.filter(user=request.user,status='active').select_related('organisation')[:6],
            'unread_count':Notification.objects.filter(user=request.user,read_at__isnull=True).count()}
