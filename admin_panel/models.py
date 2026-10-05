from django.db import models
from django.conf import settings


# -------------------- ADMIN --------------------
class AdminProfile(models.Model):
    """
    Access levels for the admin API:
    1 gallery, 4 content (courses, comments, banners, partners, invoices), 5 super admin (users, admins)
    """
    ACCESS_LEVEL_CHOICES = [
        (1, 'سطح ۱ - گالری'),
        (2, 'سطح ۲'),
        (3, 'سطح ۳'),
        (4, 'سطح ۴ - مدیریت محتوا و دوره‌ها'),
        (5, 'مدیر کل'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='admin_profile', verbose_name='کاربر')
    register_datetime = models.DateTimeField('تاریخ ثبت', auto_now_add=True)
    activity_history = models.TextField('سابقه فعالیت', null=True, blank=True)
    access_level = models.IntegerField('سطح دسترسی', choices=ACCESS_LEVEL_CHOICES, default=1)

    class Meta:
        verbose_name = 'ادمین'
        verbose_name_plural = 'ادمین‌ها'

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.email} ({self.get_access_level_display()})"


# -------------------- GALLERY --------------------
class Gallery(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField('عنوان', max_length=255)
    description = models.TextField('توضیحات', blank=True, null=True)
    image = models.ImageField('تصویر', upload_to='gallery/', blank=True, null=True)
    image_url = models.URLField('لینک تصویر (اختیاری)', max_length=500, blank=True, null=True)
    event_date = models.DateField('تاریخ رویداد', blank=True, null=True)
    uploaded_at = models.DateTimeField('تاریخ آپلود', auto_now_add=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_galleries', verbose_name='آپلود کننده')
    is_published = models.BooleanField('منتشر شده', default=False)
    tags = models.CharField('برچسب‌ها', max_length=255, blank=True, help_text='با کاما جدا کنید')
    views_count = models.PositiveIntegerField('بازدید', default=0)
    order_index = models.IntegerField('ترتیب', default=0)

    class Meta:
        ordering = ['order_index', '-uploaded_at']
        verbose_name = 'تصویر گالری'
        verbose_name_plural = 'گالری'

    @property
    def image_src(self):
        if self.image:
            return self.image.url
        return self.image_url or ''

    def __str__(self):
        return self.title


# -------------------- COMMENT --------------------
class Comment(models.Model):
    """
    Review / comment. Either about a course (course) or about a user, e.g. a teacher (student).
    New comments wait for an admin approval before being public.
    """
    class Status(models.TextChoices):
        PENDING = 'pending', 'در انتظار تایید'
        APPROVED = 'approved', 'تایید شده'
        REJECTED = 'rejected', 'رد شده'

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='received_comments', verbose_name='درباره کاربر')
    course = models.ForeignKey('users.Course', on_delete=models.CASCADE, null=True, blank=True, related_name='comments', verbose_name='دوره')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='written_comments', verbose_name='نویسنده')
    text = models.TextField('متن')
    rating = models.PositiveSmallIntegerField('امتیاز', default=5)
    status = models.CharField('وضعیت', max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField('تاریخ', auto_now_add=True)

    class Meta:
        verbose_name = 'نظر'
        verbose_name_plural = 'نظرات'
        ordering = ['-created_at']

    def __str__(self):
        target = self.course or self.student
        return f"نظر {self.author} درباره {target} ({self.get_status_display()})"


# -------------------- BANNER --------------------
class Banner(models.Model):
    title = models.CharField('عنوان', max_length=200)
    image = models.ImageField('تصویر', upload_to='banners/')
    priority = models.PositiveIntegerField('اولویت', default=1)
    link = models.URLField('لینک', null=True, blank=True)
    is_active = models.BooleanField('فعال', default=True)
    start_date = models.DateTimeField('شروع نمایش', null=True, blank=True)
    end_date = models.DateTimeField('پایان نمایش', null=True, blank=True)
    created_at = models.DateTimeField('تاریخ ایجاد', auto_now_add=True)

    class Meta:
        verbose_name = 'بنر'
        verbose_name_plural = 'بنرها'
        ordering = ['priority']

    def __str__(self):
        return self.title


# -------------------- PARTNER --------------------
class Partner(models.Model):
    title = models.CharField('عنوان', max_length=255)
    logo = models.ImageField('لوگو', upload_to='partners/')
    description = models.TextField('توضیحات', null=True, blank=True)
    link = models.URLField('لینک', null=True, blank=True)
    priority = models.PositiveIntegerField('اولویت', default=0)
    is_active = models.BooleanField('فعال', default=True)
    created_at = models.DateTimeField('تاریخ ایجاد', auto_now_add=True)

    class Meta:
        ordering = ['priority', '-created_at']
        verbose_name = 'همکار'
        verbose_name_plural = 'همکاران'

    def __str__(self):
        return self.title
