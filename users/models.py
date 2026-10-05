from django.contrib.auth.models import AbstractUser
from django.db import models


# -------------------- USER --------------------
class User(AbstractUser):
    """
    Base user (students, teachers and admins). The email is the login identifier.
    """
    class Gender(models.TextChoices):
        MALE = 'male', 'مرد'
        FEMALE = 'female', 'زن'

    birthday_date = models.DateField('تاریخ تولد', null=True, blank=True)
    national_id = models.CharField('کد ملی', max_length=20, null=True, blank=True)
    phone_number = models.CharField('شماره موبایل', max_length=20, null=True, blank=True)
    gender = models.CharField('جنسیت', max_length=10, choices=Gender.choices, null=True, blank=True)
    fathers_name = models.CharField('نام پدر', max_length=100, null=True, blank=True)
    education_level = models.CharField('تحصیلات', max_length=100, null=True, blank=True)
    profile_image = models.ImageField('تصویر پروفایل', upload_to='profile_images/', null=True, blank=True)

    email = models.EmailField('ایمیل', unique=True)

    REQUIRED_FIELDS = ['email', 'first_name', 'last_name']
    USERNAME_FIELD = 'username'

    class Meta(AbstractUser.Meta):
        verbose_name = 'کاربر'
        verbose_name_plural = 'کاربران'

    @property
    def is_teacher(self):
        return hasattr(self, 'teacher')

    @property
    def is_approved_teacher(self):
        return hasattr(self, 'teacher') and self.teacher.is_approved

    @property
    def popularity(self):
        """Average rating of approved comments received by this user"""
        return self.received_comments.filter(status='approved').aggregate(
            avg_rating=models.Avg('rating')
        )['avg_rating'] or 0

    def __str__(self):
        name = self.get_full_name()
        return f"{name} ({self.email})" if name else self.email


# -------------------- TEACHER --------------------
class Teacher(models.Model):
    """
    Teacher profile, linked one-to-one with a User.
    A teacher can manage courses only after an admin approves the profile.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher', verbose_name='کاربر')
    education_degree = models.CharField('مدرک تحصیلی', max_length=100, null=True, blank=True)
    academic_field = models.CharField('رشته', max_length=100, null=True, blank=True)
    bio = models.TextField('بیوگرافی', null=True, blank=True)
    profile_image = models.ImageField('تصویر', upload_to='teacher_images/', null=True, blank=True)
    is_approved = models.BooleanField('تایید شده', default=False)

    class Meta:
        verbose_name = 'استاد'
        verbose_name_plural = 'اساتید'

    def __str__(self):
        return self.user.get_full_name() or self.user.email


# -------------------- COURSE --------------------
class Course(models.Model):
    title = models.CharField('عنوان', max_length=200)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='courses', verbose_name='استاد')
    start_date = models.DateField('تاریخ شروع', null=True, blank=True)
    end_date = models.DateField('تاریخ پایان', null=True, blank=True)
    duration = models.IntegerField('مدت (ساعت)', null=True, blank=True)
    exam_date = models.DateField('تاریخ آزمون', null=True, blank=True)
    cost = models.DecimalField('قیمت (تومان)', max_digits=12, decimal_places=0, null=True, blank=True)
    discount_price = models.DecimalField('قیمت با تخفیف', max_digits=12, decimal_places=0, null=True, blank=True)
    logo = models.ImageField('تصویر دوره', upload_to='course_logos/', null=True, blank=True)
    description = models.TextField('توضیحات', null=True, blank=True)
    short_description = models.CharField('توضیح کوتاه', max_length=300, null=True, blank=True)
    category = models.CharField('دسته‌بندی', max_length=100, null=True, blank=True)
    level = models.CharField('سطح', max_length=50, null=True, blank=True)
    tags = models.CharField('برچسب‌ها', max_length=255, null=True, blank=True)
    created_at = models.DateTimeField('تاریخ ایجاد', auto_now_add=True)
    last_updated = models.DateTimeField('آخرین ویرایش', auto_now=True)
    is_active = models.BooleanField('فعال', default=True)
    limit_students = models.IntegerField('ظرفیت', null=True, blank=True)
    rating_avg = models.DecimalField('میانگین امتیاز', max_digits=2, decimal_places=1, null=True, blank=True)
    requirements = models.TextField('پیش‌نیازها', null=True, blank=True)

    class Meta:
        verbose_name = 'دوره'
        verbose_name_plural = 'دوره‌ها'
        ordering = ['-created_at']

    @property
    def final_price(self):
        if self.discount_price is not None:
            return self.discount_price
        return self.cost or 0

    def __str__(self):
        return self.title


# -------------------- COURSE SESSION --------------------
class CourseSession(models.Model):
    """
    A session (lesson) of a course with its video / pdf.
    Files are only reachable by enrolled (paid) students, the teacher and admins,
    except for free preview sessions.
    """
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sessions', verbose_name='دوره')
    title = models.CharField('عنوان', max_length=200)
    description = models.TextField('توضیحات', null=True, blank=True)
    order = models.PositiveIntegerField('ترتیب', default=0)
    is_free = models.BooleanField('پیش‌نمایش رایگان', default=False)
    video = models.FileField('ویدیو', upload_to='sessions/videos/', null=True, blank=True)
    pdf = models.FileField('جزوه (PDF)', upload_to='sessions/pdfs/', null=True, blank=True)
    created_at = models.DateTimeField('تاریخ ایجاد', auto_now_add=True)

    class Meta:
        verbose_name = 'جلسه'
        verbose_name_plural = 'جلسات'
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.course.title} - {self.title}"


# -------------------- INVOICE (enrollment) --------------------
class Invoice(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='invoices', verbose_name='دانشجو')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='invoices', verbose_name='دوره')
    date_time = models.DateTimeField('تاریخ ثبت‌نام', auto_now_add=True)
    amount = models.DecimalField('مبلغ (تومان)', max_digits=12, decimal_places=0, null=True, blank=True)
    paid = models.BooleanField('پرداخت شده', default=False)
    paid_at = models.DateTimeField('تاریخ پرداخت', null=True, blank=True)
    grade = models.CharField('نتیجه', max_length=10, null=True, blank=True)
    score = models.DecimalField('نمره', max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ('student', 'course')
        verbose_name = 'ثبت‌نام / فاکتور'
        verbose_name_plural = 'ثبت‌نام‌ها / فاکتورها'
        ordering = ['-date_time']

    def __str__(self):
        return f"فاکتور {self.id} - {self.student.email} - {self.course.title}"
