"""Opt-in fictional demonstration content. NEVER run against production data."""
import os
from datetime import timedelta
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from exchange.models import Organisation,Membership,Credential,Resource

class Command(BaseCommand):
    help='Create fictional KINETRA demo institution, accounts and resources.'
    @transaction.atomic
    def handle(self,*args,**kwargs):
        if os.getenv('DJANGO_DEBUG','false').lower()!='true' and os.getenv('ALLOW_SEED_DEMO')!='yes':
            raise CommandError('Demo seeding disabled outside development. Set ALLOW_SEED_DEMO=yes intentionally.')
        password=os.getenv('DEMO_PASSWORD')
        if not password or len(password)<12:
            raise CommandError('Set DEMO_PASSWORD to a unique, >=12 character password. Never reuse a real password.')
        org,_=Organisation.objects.get_or_create(slug='northfield-innovation',defaults={
            'name':'Northfield Innovation Campus','description':'A fictional university innovation centre for evaluation.','city':'Jaipur','contact_email':'admin@example.invalid'})
        users=get_user_model()
        people=[('demo_admin','Morgan','Patel','admin'),('demo_owner','Riya','Shah','owner'),
                ('demo_student','Aarav','Mehta','member'),('demo_student2','Noor','Kapoor','member')]
        objs={}
        for username,first,last,role in people:
            u,created=users.objects.get_or_create(username=username,defaults={'first_name':first,'last_name':last,'email':f'{username}@example.invalid'})
            if created:u.set_password(password);u.save()
            Membership.objects.update_or_create(user=u,organisation=org,defaults={'role':role,'status':'active'})
            objs[role if role not in objs else username]=u
        m=Membership.objects.get(user=objs['member'],organisation=org)
        Credential.objects.update_or_create(member=m,title='3D Printer Safety',defaults={'status':'verified','reviewed_by':objs['admin']})
        seeds=[
          ('Ultimaker S5 · 3D Printer','fabrication','Professional dual-extrusion 3D printer for prototypes and rapid fabrication.','Innovation Lab · Room 204','3D Printer Safety',True),
          ('Creative Media Studio','media','Camera, lighting and recording setup for student media projects.','Media Wing · Studio B','',False),
          ('Design Collaboration Room','space','Calm, flexible meeting space for small project teams.','Academic Block · Floor 2','',False),
          ('Electronics Testing Bench','tools','Oscilloscope, multimeter and regulated power supply for circuit analysis.','Engineering Lab · Bay 03','Electronics Lab Safety',True),
          ('High-Performance Compute Station','computing','GPU workstation for demanding design and research workloads.','Research Centre · Desk 12','',False),
          ('Applied Robotics Laboratory','lab','Supervised robotics workbench for prototyping and controlled experiments.','Robotics Centre · Lab 1','Robotics Lab Orientation',True),
        ]
        for name,category,summary,location,training,supervision in seeds:
            Resource.objects.get_or_create(organisation=org,name=name,defaults={'owner':objs['owner'],'category':category,
                'summary':summary,'description':summary+' Available to verified campus members for authorised educational projects.',
                'location':location,'required_training':training,'requires_supervision':supervision,
                'usage_rules':'Reserve a slot, present valid institutional identification, follow staff instructions, and return the resource in the recorded condition.'})
        self.stdout.write(self.style.SUCCESS('Fictional demo data created. Login as demo_admin, demo_owner, demo_student or demo_student2 using DEMO_PASSWORD.'))
