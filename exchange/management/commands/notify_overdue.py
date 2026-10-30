"""Run with cron / task scheduler; reminders are persistent in-app notifications."""
from django.core.management.base import BaseCommand
from django.utils import timezone
from exchange.models import Booking,Notification

class Command(BaseCommand):
    help='Generate at most one overdue alert per booking per day.'
    def handle(self,*args,**kwargs):
        qs=Booking.objects.filter(status__in=['active','return_pending'],end__lt=timezone.now()).select_related('borrower','resource')
        day=timezone.localdate().isoformat()
        created=0
        for booking in qs.iterator():
            title=f'Overdue return · {day} · {booking.public_id}'
            if not Notification.objects.filter(user=booking.borrower,title=title).exists():
                Notification.objects.create(user=booking.borrower,title=title,body=f'{booking.resource.name} has passed its expected return time.',link=f'/bookings/{booking.pk}/')
                created+=1
        self.stdout.write(f'Generated {created} overdue alerts.')
