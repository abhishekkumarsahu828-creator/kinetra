"""One-time controlled onboarding of an organisation and its first administrator."""
import os
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from exchange.models import Organisation,Membership
from exchange.services import audit

class Command(BaseCommand):
    help='Bootstrap a real organisation and associate an EXISTING verified account as admin. Authorized operators only.'
    def add_arguments(self,parser):
        parser.add_argument('--name',required=True)
        parser.add_argument('--slug',required=True)
        parser.add_argument('--username',required=True)
        parser.add_argument('--city',default='')
        parser.add_argument('--email',default='',help='Required when creating a new admin account')
    @transaction.atomic
    def handle(self,*args,**options):
        User=get_user_model()
        user=User.objects.filter(username=options['username'],is_active=True).first()
        if user is None:
            password=os.getenv('BOOTSTRAP_PASSWORD','')
            if not options['email'] or len(password)<12:
                raise CommandError('For a new administrator, supply --email and BOOTSTRAP_PASSWORD (12+ characters) through the operator environment.')
            if User.objects.filter(email__iexact=options['email']).exists():
                raise CommandError('An account with that email already exists.')
            user=User.objects.create_user(username=options['username'],email=options['email'],password=password)
        if Organisation.objects.filter(slug=options['slug']).exists():
            raise CommandError('Organisation slug already exists; refusing to change existing privileges.')
        org=Organisation.objects.create(name=options['name'],slug=options['slug'],city=options['city'])
        membership=Membership.objects.create(user=user,organisation=org,role='admin',status='active',reviewed_by=user)
        audit(org,user,'organisation.bootstrapped',org,first_admin=user.username)
        audit(org,user,'membership.initial_admin_granted',membership)
        self.stdout.write(self.style.SUCCESS(f'Organisation {org.slug} created with admin {user.username}. Confirm real identity out of band before use.'))
