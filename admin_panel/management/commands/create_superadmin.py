from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from admin_panel.models import AdminProfile


class Command(BaseCommand):
    """
    Create (or update) a super admin usable both in /admin/ and in the admin API (access level 5)
    python manage.py create_superadmin --email admin@example.com --password '...'
    """
    help = 'Create or update a super admin (Django superuser + AdminProfile level 5)'

    def add_arguments(self, parser):
        parser.add_argument('--email', required=True)
        parser.add_argument('--password', required=True)
        parser.add_argument('--first-name', default='مدیر')
        parser.add_argument('--last-name', default='سایت')

    def handle(self, *args, **options):
        User = get_user_model()
        email = options['email'].lower()
        if len(options['password']) < 10:
            raise CommandError('Password must be at least 10 characters.')

        user = User.objects.filter(email__iexact=email).first()
        created = user is None
        if created:
            user = User(username=email, email=email)

        user.first_name = options['first_name']
        user.last_name = options['last_name']
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(options['password'])
        user.save()

        AdminProfile.objects.update_or_create(user=user, defaults={'access_level': 5})

        self.stdout.write(self.style.SUCCESS(f"Super admin {'created' if created else 'updated'}: {email}"))
