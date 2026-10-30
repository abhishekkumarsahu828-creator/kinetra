"""Create a superuser from temporary Render environment variables."""
import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Create a superuser from temporary KINETRA bootstrap environment variables.'

    def handle(self, *args, **options):
        if os.getenv('KINETRA_CREATE_SUPERUSER_ONCE', '').lower() != 'yes':
            raise CommandError('Set KINETRA_CREATE_SUPERUSER_ONCE=yes to enable this one-time bootstrap.')

        username = os.getenv('KINETRA_SUPERUSER_USERNAME', '').strip()
        email = os.getenv('KINETRA_SUPERUSER_EMAIL', '').strip()
        password = os.getenv('KINETRA_SUPERUSER_PASSWORD', '')
        if not username or not email or not password:
            raise CommandError('Set KINETRA_SUPERUSER_USERNAME, KINETRA_SUPERUSER_EMAIL, and KINETRA_SUPERUSER_PASSWORD.')

        User = get_user_model()
        existing = User.objects.filter(username=username).first()
        if existing:
            if existing.is_superuser:
                self.stdout.write('That superuser already exists; password left unchanged.')
                return
            raise CommandError('That username already belongs to a non-superuser account. Choose another username.')

        candidate = User(username=username, email=email)
        try:
            validate_password(password, user=candidate)
        except ValidationError as exc:
            raise CommandError('; '.join(exc.messages)) from None

        User.objects.db_manager().create_superuser(
            username=username,
            email=email,
            password=password,
        )
        self.stdout.write(self.style.SUCCESS('Superuser created. Remove the temporary bootstrap variables in Render now.'))
