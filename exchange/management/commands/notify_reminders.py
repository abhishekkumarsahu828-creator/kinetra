"""Create in-app reminders for confirmed reservations approaching their start."""
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from exchange.models import Booking,Notification

class Command(BaseCommand):
    help='Create one in-app upcoming reminder per approved booking.'
    def handle(self,*args,**kwargs):
        now=timezone.now()
        due=Booking.objects.filter(status='approved',start__gt=now,start__lte=now+timedelta(hours=24)).select_related('borrower','resource')
        created=0
        for booking in due.iterator():
            title=f'Upcoming booking · {booking.public_id}'
            if not Notification.objects.filter(user=booking.borrower,title=title).exists():
                Notification.objects.create(user=booking.borrower,title=title,
                    body=f'{booking.resource.name} starts {timezone.localtime(booking.start):%d %b %H:%M}. Please prepare for check-in.',link=f'/bookings/{booking.pk}/')
                created+=1
        self.stdout.write(f'Generated {created} upcoming reminders.')
