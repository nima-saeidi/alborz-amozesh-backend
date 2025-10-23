# ===========================================
# users/models.py
# ===========================================
from django.contrib.auth.models import AbstractUser
from django.db import models

# -------------------- USER --------------------
class User(AbstractUser):
    birthday_date = models.DateField(null=True, blank=True)
    national_id = models.CharField(max_length=20, null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)
    fathers_name = models.CharField(max_length=100, null=True, blank=True)
    education_level = models.CharField(max_length=100, null=True, blank=True)
    profile_image = models.ImageField(upload_to='profile_images/', null=True, blank=True)  # profile picture

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"



# -------------------- TEACHER --------------------
class Teacher(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    education_degree = models.CharField(max_length=100, null=True, blank=True)
    academic_field = models.CharField(max_length=100, null=True, blank=True)
    last_login = models.DateTimeField(null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    profile_image = models.ImageField(upload_to='teacher_images/', null=True, blank=True)  # profile picture

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    
# -------------------- COURSE --------------------
class Course(models.Model):
    title = models.CharField(max_length=200)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='courses')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    duration = models.IntegerField(null=True, blank=True)
    notes_file = models.CharField(max_length=255, null=True, blank=True)
    videos = models.TextField(null=True, blank=True)
    exam_date = models.DateField(null=True, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    logo = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    short_description = models.CharField(max_length=300, null=True, blank=True)
    category = models.CharField(max_length=100, null=True, blank=True)
    level = models.CharField(max_length=50, null=True, blank=True)
    tags = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    limit_students = models.IntegerField(null=True, blank=True)
    rating_avg = models.DecimalField(max_digits=2, decimal_places=1, null=True, blank=True)
    requirements = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.title


# -------------------- INVOICE --------------------
class Invoice(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='invoices')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='invoices')
    date_time = models.DateTimeField(auto_now_add=True)
    paid = models.BooleanField(default=False)
    grade = models.CharField(max_length=10, null=True, blank=True)
    score = models.DecimalField(max_digits=2, decimal_places=1, null=True, blank=True)

    def __str__(self):
        return f"Invoice {self.id} - {self.student.email}"
