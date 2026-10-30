"""Give active platform superusers reviewer access to fictional demo organisations."""
from django.conf import settings
from django.db import migrations


def grant_demo_admin_access(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    User = apps.get_model(settings.AUTH_USER_MODEL)
    Organisation = apps.get_model('exchange', 'Organisation')
    Membership = apps.get_model('exchange', 'Membership')
    AuditEvent = apps.get_model('exchange', 'AuditEvent')

    organisations = Organisation.objects.using(db_alias).filter(
        slug__startswith='kinetra-demo-', is_active=True,
    )
    administrators = User.objects.using(db_alias).filter(
        is_active=True, is_superuser=True,
    ).order_by('pk')

    for administrator in administrators:
        for organisation in organisations:
            membership, _ = Membership.objects.using(db_alias).update_or_create(
                user=administrator,
                organisation=organisation,
                defaults={'role': 'admin', 'status': 'active'},
            )
            AuditEvent.objects.using(db_alias).create(
                organisation=organisation,
                actor=administrator,
                verb='demo.admin_access_granted',
                object_type='Membership',
                object_id=membership.pk,
                details={'reason': 'Enable the platform superuser to verify fictional demo memberships.'},
            )


class Migration(migrations.Migration):
    dependencies = [('exchange', '0002_demo_catalog')]

    operations = [migrations.RunPython(grant_demo_admin_access, migrations.RunPython.noop)]
