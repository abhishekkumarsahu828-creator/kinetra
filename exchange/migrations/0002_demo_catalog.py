"""Add fictional preview organisations and resource listings."""
from datetime import time

from django.conf import settings
from django.db import migrations


DEMO_OWNER_EMAIL = 'demo-owner@kinetra.invalid'


def seed_demo_catalog(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    User = apps.get_model(settings.AUTH_USER_MODEL)
    Organisation = apps.get_model('exchange', 'Organisation')
    Resource = apps.get_model('exchange', 'Resource')

    users = User.objects.using(db_alias)
    owner = None
    for suffix in range(1000):
        username = 'kinetra_demo_catalog' if suffix == 0 else f'kinetra_demo_catalog_{suffix}'
        existing = users.filter(username=username).first()
        if existing:
            if (existing.email == DEMO_OWNER_EMAIL and not existing.is_active
                    and existing.password.startswith('!')):
                owner = existing
                break
            continue
        owner = User(
            username=username,
            first_name='KINETRA Demo',
            last_name='Catalogue',
            email=DEMO_OWNER_EMAIL,
            password='!',
            is_active=False,
        )
        owner.save(using=db_alias)
        break
    if owner is None:
        raise RuntimeError('Could not reserve an inactive owner for KINETRA sample listings.')

    organisations = [
        {
            'slug': 'kinetra-demo-institute',
            'name': 'KINETRA Demo Institute',
            'city': 'Jaipur',
            'description': 'Fictional demo organisation. Listings and contact details are sample data for preview only.',
            'contact_email': 'institute-preview@example.invalid',
        },
        {
            'slug': 'kinetra-demo-makerspace',
            'name': 'KINETRA Demo Makerspace',
            'city': 'Pune',
            'description': 'Fictional demo makerspace. Listings and contact details are sample data for preview only.',
            'contact_email': 'makerspace-preview@example.invalid',
        },
    ]

    catalog = {
        'kinetra-demo-institute': [
            ('Ultimaker S5 3D Printer', 'fabrication', 'DEMO LISTING · Dual extrusion 3D printer for prototype parts.', 'Innovation Lab · Room 204', 'PLA and PETG printing; 0.4 mm nozzle; build volume 330 × 240 × 300 mm.', 'Introductory 3D printer safety', True),
            ('Robotics Prototyping Bench', 'lab', 'DEMO LISTING · A supervised bench for small robotics prototypes.', 'Engineering Wing · Lab 1', 'Modular work surface, sensor kits and low-voltage power supplies.', 'Robotics lab orientation', True),
            ('Project Collaboration Room', 'space', 'DEMO LISTING · A small meeting room for student project teams.', 'Learning Centre · Room 12', 'Seats six; whiteboard and display screen.', '', False),
        ],
        'kinetra-demo-makerspace': [
            ('Podcast and Media Studio', 'media', 'DEMO LISTING · A sample recording space with microphones and lights.', 'Media Hub · Studio B', 'Two microphones, audio interface and basic lighting kit.', '', False),
            ('Electronics Testing Bench', 'tools', 'DEMO LISTING · Test circuits with sample bench instruments.', 'Workshop · Bay 03', 'Oscilloscope, multimeter and current-limited bench supply.', 'Electrical workshop safety', True),
            ('GPU Design Workstation', 'computing', 'DEMO LISTING · A sample workstation for 3D design and rendering.', 'Digital Lab · Desk 08', 'Workstation with a graphics card suitable for CAD and rendering practice.', '', False),
        ],
    }

    for data in organisations:
        org, _ = Organisation.objects.using(db_alias).get_or_create(
            slug=data['slug'], defaults=data,
        )
        for name, category, summary, location, specs, training, supervised in catalog[data['slug']]:
            Resource.objects.using(db_alias).get_or_create(
                organisation=org,
                name=name,
                defaults={
                    'owner': owner,
                    'category': category,
                    'summary': summary,
                    'description': f'{summary} This is fictional sample content for the KINETRA preview and does not represent a real facility or confirmed equipment.',
                    'location': location,
                    'equipment_specs': specs,
                    'usage_rules': 'Fictional preview listing only. Do not travel to this location or rely on this listing for access or safety instructions.',
                    'required_training': training,
                    'requires_supervision': supervised,
                    'max_hours': 3,
                    'weekly_hours_limit': 6,
                    'advance_booking_days': 14,
                    'open_time': time(9, 0),
                    'close_time': time(18, 0),
                    'available_days': '0,1,2,3,4',
                    'status': 'active',
                },
            )


class Migration(migrations.Migration):
    dependencies = [('exchange', '0001_initial')]

    operations = [migrations.RunPython(seed_demo_catalog, migrations.RunPython.noop)]
