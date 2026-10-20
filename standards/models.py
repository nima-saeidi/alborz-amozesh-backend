from django.core.validators import FileExtensionValidator
from django.db import models


# -------------------- CATEGORY --------------------
class StandardCategory(models.Model):
    """Group of standards (e.g. فناوری اطلاعات, برق, مدیریت)"""
    title = models.CharField('عنوان', max_length=150, unique=True)
    order = models.IntegerField('ترتیب', default=0)

    class Meta:
        verbose_name = 'گروه استاندارد'
        verbose_name_plural = 'گروه‌های استاندارد'
        ordering = ['order', 'title']

    def __str__(self):
        return self.title


# -------------------- STANDARD --------------------
class TechnicalStandard(models.Model):
    """A technical & vocational training standard, published as a PDF file"""
    title = models.CharField('عنوان استاندارد', max_length=255)
    code = models.CharField('کد استاندارد', max_length=60, blank=True)
    category = models.ForeignKey(StandardCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='standards', verbose_name='گروه')
    level = models.CharField('درجه / سطح', max_length=60, blank=True)
    hours = models.PositiveIntegerField('مدت آموزش (ساعت)', null=True, blank=True)
    description = models.TextField('توضیحات', blank=True)
    pdf = models.FileField('فایل PDF', upload_to='standards/', validators=[FileExtensionValidator(['pdf'])])
    is_published = models.BooleanField('منتشر شده', default=True)
    order = models.IntegerField('ترتیب', default=0)
    downloads = models.PositiveIntegerField('تعداد دانلود', default=0)
    created_at = models.DateTimeField('تاریخ ثبت', auto_now_add=True)
    updated_at = models.DateTimeField('آخرین ویرایش', auto_now=True)

    class Meta:
        verbose_name = 'استاندارد فنی و حرفه‌ای'
        verbose_name_plural = 'استانداردهای فنی و حرفه‌ای'
        ordering = ['order', '-created_at']

    @property
    def file_size(self):
        try:
            return self.pdf.size
        except (OSError, ValueError):
            return None

    def __str__(self):
        return f"{self.title} ({self.code})" if self.code else self.title
