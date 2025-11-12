from django.apps import AppConfig
from django.contrib.auth import get_user_model

#NOTE this is tmp for creating superadmin
class AdminPanelConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'admin_panel'

    def ready(self):
        from django.db.utils import OperationalError
        from django.db.models import ObjectDoesNotExist
        User = get_user_model()
        from .models import AdminProfile

        try:
            # if there is no superuser 
            if not User.objects.filter(is_superuser=True).exists():
                # creat superuser
                superuser = User.objects.create_superuser(
                    username='admin',
                    email='admin@example.com',
                    password='admin123',
                    first_name='Admin',
                    last_name='User'
                )
                # creat AdminProfile با access_level=5
                AdminProfile.objects.create(
                    user=superuser,
                    access_level=5
                )
        except (OperationalError, ObjectDoesNotExist):
            pass