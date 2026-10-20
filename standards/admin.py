from django.contrib import admin, messages
from django.db.models import Count
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.decorators import display

from users.admin import jalali
from .models import StandardCategory, TechnicalStandard


@admin.register(StandardCategory)
class StandardCategoryAdmin(ModelAdmin):
    list_display = ('title', 'count', 'order')
    list_editable = ('order',)
    search_fields = ('title',)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(standards_total=Count('standards'))

    @display(description='تعداد استاندارد', ordering='standards_total')
    def count(self, obj):
        return obj.standards_total


@admin.register(TechnicalStandard)
class TechnicalStandardAdmin(ModelAdmin):
    list_display = ('title', 'code', 'category', 'level', 'file_link', 'downloads', 'is_published', 'order', 'created')
    list_display_links = ('title',)
    list_filter = ('is_published', 'category')
    list_filter_submit = True
    list_editable = ('is_published', 'order')
    search_fields = ('title', 'code', 'description')
    autocomplete_fields = ('category',)
    readonly_fields = ('downloads', 'created_at', 'updated_at', 'file_link')
    list_per_page = 30
    actions = ('publish', 'unpublish')
    fieldsets = (
        (None, {'fields': ('title', ('code', 'category'), ('level', 'hours'), 'description')}),
        ('فایل', {'fields': ('pdf', 'file_link')}),
        ('انتشار', {'fields': (('is_published', 'order'), 'downloads', ('created_at', 'updated_at'))}),
    )

    @display(description='فایل فعلی')
    def file_link(self, obj):
        if obj.pk and obj.pdf:
            return format_html('<a href="{}" target="_blank" class="text-primary-600">مشاهده فایل</a>', obj.pdf.url)
        return '-'

    @display(description='تاریخ ثبت', ordering='created_at')
    def created(self, obj):
        return jalali(obj.created_at, False)

    @admin.action(description='انتشار موارد انتخاب شده')
    def publish(self, request, queryset):
        self.message_user(request, f'{queryset.update(is_published=True)} استاندارد منتشر شد.', messages.SUCCESS)

    @admin.action(description='خارج کردن از انتشار')
    def unpublish(self, request, queryset):
        self.message_user(request, f'{queryset.update(is_published=False)} استاندارد از انتشار خارج شد.', messages.WARNING)
