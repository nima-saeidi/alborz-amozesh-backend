from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

# -------------------- ADMIN --------------------
class AdminProfile(models.Model):
    ACCESS_LEVEL_CHOICES = [
        (1, 'Level 1'),
        (2, 'Level 2'),
        (3, 'Level 3'),
        (4, 'Level 4'),
        (5, 'SuperAdmin'),
    ]
        
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_profile')
    register_datetime = models.DateTimeField(auto_now_add=True)
    activity_history = models.TextField(null=True, blank=True)
    access_level = models.IntegerField(choices=ACCESS_LEVEL_CHOICES, default=1)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} ({self.get_access_level_display()})"
