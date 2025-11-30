from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings

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


# -------------------- GALLERY --------------------
class Gallery(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    image_url = models.URLField(max_length=500)
    event_date = models.DateField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='uploaded_galleries')
    is_published = models.BooleanField(default=False)
    tags = models.CharField(max_length=255, blank=True, help_text="Comma separated tags")
    views_count = models.PositiveIntegerField(default=0)
    order_index = models.IntegerField(default=0)

    class Meta:
        ordering = ['order_index', '-uploaded_at']
        verbose_name = "Gallery Item"
        verbose_name_plural = "Gallery Items"

    def __str__(self):
        return f"{self.title} ({'Published' if self.is_published else 'Draft'})"

# -------------------- Commnet --------------------
class Comment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='written_comments')
    text = models.TextField()
    rating = models.PositiveSmallIntegerField(default=5)
    status = models.CharField(max_length=10,choices=Status.choices,default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.author} on {self.student} ({self.status})"

# -------------------- Banner --------------------
class Banner(models.Model):
    title = models.CharField(max_length=200)
    image = models.ImageField(upload_to='banners/')
    priority = models.PositiveIntegerField(default=1)
    link = models.URLField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

# ---------------- Our Collaborators ----------------
class Partner(models.Model):
    title = models.CharField(max_length=255)
    logo = models.ImageField(upload_to='partners/')
    description = models.TextField(null=True, blank=True)
    link = models.URLField(null=True, blank=True)
    priority = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['priority', '-created_at']

    def __str__(self):
        return self.title
