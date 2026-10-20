"""
Student panel data kept on the server: favorites, lesson progress, certificates,
support tickets, notifications, contact-form messages and newsletter sign-ups.
"""
import os
import secrets

from django.conf import settings
from django.db import models

from users.models import Course, CourseSession

User = settings.AUTH_USER_MODEL


# -------------------- LEARNING --------------------
class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites', verbose_name='کاربر')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='favorited_by', verbose_name='دوره')
    created_at = models.DateTimeField('تاریخ', auto_now_add=True)

    class Meta:
        verbose_name = 'علاقه‌مندی'
        verbose_name_plural = 'علاقه‌مندی‌ها'
        constraints = [models.UniqueConstraint(fields=['user', 'course'], name='unique_favorite')]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} - {self.course}'


class SessionProgress(models.Model):
    """A session the student marked as watched"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='session_progress', verbose_name='کاربر')
    session = models.ForeignKey(CourseSession, on_delete=models.CASCADE, related_name='progress', verbose_name='جلسه')
    completed_at = models.DateTimeField('زمان تکمیل', auto_now_add=True)

    class Meta:
        verbose_name = 'پیشرفت جلسه'
        verbose_name_plural = 'پیشرفت جلسات'
        constraints = [models.UniqueConstraint(fields=['user', 'session'], name='unique_session_progress')]

    def __str__(self):
        return f'{self.user} - {self.session}'


def new_certificate_code():
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'  # no 0/O or 1/I look-alikes
    while True:
        code = 'ALB-' + ''.join(secrets.choice(alphabet) for _ in range(8))
        if not Certificate.objects.filter(code=code).exists():
            return code


class Certificate(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='certificates', verbose_name='دانشجو')
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name='certificates', verbose_name='دوره')
    code = models.CharField('کد استعلام', max_length=20, unique=True, default=new_certificate_code, editable=False)
    full_name = models.CharField('نام روی گواهی', max_length=300, blank=True, help_text='خالی بماند تا نام کاربر استفاده شود')
    grade = models.CharField('نتیجه / نمره', max_length=50, blank=True)
    issued_at = models.DateTimeField('تاریخ صدور', auto_now_add=True)
    is_revoked = models.BooleanField('باطل شده', default=False)

    class Meta:
        verbose_name = 'گواهی‌نامه'
        verbose_name_plural = 'گواهی‌نامه‌ها'
        constraints = [models.UniqueConstraint(fields=['user', 'course'], name='unique_certificate')]
        ordering = ['-issued_at']

    def save(self, *args, **kwargs):
        if not self.full_name:
            self.full_name = self.user.get_full_name() or self.user.username
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.code} - {self.full_name}'


# -------------------- SUPPORT --------------------
def ticket_attachment_path(instance, filename):
    """Random folder per file so attachment links cannot be guessed"""
    name, ext = os.path.splitext(os.path.basename(filename))
    return f'tickets/{secrets.token_hex(16)}/{name[:60]}{ext.lower()}'


class Ticket(models.Model):
    class Status(models.TextChoices):
        OPEN = 'open', 'در انتظار پاسخ'
        ANSWERED = 'answered', 'پاسخ داده شده'
        CLOSED = 'closed', 'بسته شده'

    class Department(models.TextChoices):
        EDUCATION = 'education', 'آموزشی'
        FINANCE = 'finance', 'مالی'
        TECHNICAL = 'technical', 'فنی'
        OTHER = 'other', 'سایر'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets', verbose_name='کاربر')
    subject = models.CharField('موضوع', max_length=200)
    department = models.CharField('بخش', max_length=20, choices=Department.choices, default=Department.EDUCATION)
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets', verbose_name='دوره مرتبط')
    status = models.CharField('وضعیت', max_length=10, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField('تاریخ ثبت', auto_now_add=True)
    updated_at = models.DateTimeField('آخرین تغییر', auto_now=True)

    class Meta:
        verbose_name = 'تیکت'
        verbose_name_plural = 'تیکت‌ها'
        ordering = ['-updated_at']

    def __str__(self):
        return f'#{self.id} {self.subject}'


class TicketMessage(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='messages', verbose_name='تیکت')
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='نویسنده')
    is_staff_reply = models.BooleanField('پاسخ پشتیبانی', default=False)
    text = models.TextField('متن')
    attachment = models.FileField('پیوست', upload_to=ticket_attachment_path, null=True, blank=True)
    created_at = models.DateTimeField('زمان', auto_now_add=True)

    class Meta:
        verbose_name = 'پیام تیکت'
        verbose_name_plural = 'پیام‌های تیکت'
        ordering = ['created_at']

    def __str__(self):
        return self.text[:50]


class Notification(models.Model):
    """For one user, or for everyone when user is empty (an announcement)"""
    class Kind(models.TextChoices):
        COURSE = 'course', 'دوره‌ها'
        TICKET = 'ticket', 'پشتیبانی'
        PAYMENT = 'payment', 'مالی'
        GENERAL = 'general', 'اطلاعیه'

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications', verbose_name='کاربر', help_text='خالی = برای همه کاربران')
    kind = models.CharField('نوع', max_length=10, choices=Kind.choices, default=Kind.GENERAL)
    title = models.CharField('عنوان', max_length=200)
    text = models.TextField('متن', blank=True)
    link = models.CharField('لینک داخل سایت', max_length=300, blank=True, help_text='مثلاً /courses/12')
    created_at = models.DateTimeField('زمان', auto_now_add=True)
    read_by = models.ManyToManyField(User, blank=True, related_name='read_notifications', verbose_name='خوانده‌شده توسط')

    class Meta:
        verbose_name = 'اعلان'
        verbose_name_plural = 'اعلان‌ها'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class ContactMessage(models.Model):
    name = models.CharField('نام', max_length=150)
    phone = models.CharField('تلفن', max_length=30, blank=True)
    email = models.EmailField('ایمیل', blank=True)
    subject = models.CharField('موضوع', max_length=200, blank=True)
    message = models.TextField('پیام')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='کاربر')
    is_handled = models.BooleanField('بررسی شده', default=False)
    created_at = models.DateTimeField('زمان', auto_now_add=True)

    class Meta:
        verbose_name = 'پیام تماس'
        verbose_name_plural = 'پیام‌های تماس با ما'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name}: {self.subject or self.message[:40]}'


class NewsletterSubscriber(models.Model):
    phone_number = models.CharField('شماره موبایل', max_length=20, unique=True)
    is_active = models.BooleanField('فعال', default=True)
    created_at = models.DateTimeField('تاریخ عضویت', auto_now_add=True)

    class Meta:
        verbose_name = 'عضو خبرنامه'
        verbose_name_plural = 'اعضای خبرنامه پیامکی'
        ordering = ['-created_at']

    def __str__(self):
        return self.phone_number
