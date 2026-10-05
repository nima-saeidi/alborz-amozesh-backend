from django.contrib import admin, messages
from django.utils.html import format_html

from users.admin import jalali
from .models import AdminProfile, Gallery, Comment, Banner, Partner


@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'access_level', 'registered')
    list_filter = ('access_level',)
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    autocomplete_fields = ('user',)

    @admin.display(description='تاریخ ثبت', ordering='register_datetime')
    def registered(self, obj):
        return jalali(obj.register_datetime, False)


@admin.register(Gallery)
class GalleryAdmin(admin.ModelAdmin):
    list_display = ('thumbnail', 'title', 'is_published', 'event', 'views_count', 'order_index')
    list_display_links = ('thumbnail', 'title')
    list_filter = ('is_published',)
    search_fields = ('title', 'description', 'tags')
    readonly_fields = ('uploaded_at', 'uploaded_by', 'views_count', 'preview')
    list_editable = ('is_published', 'order_index')
    fields = ('title', 'description', 'preview', 'image', 'image_url', 'event_date', 'tags', 'is_published', 'order_index', 'uploaded_by', 'uploaded_at', 'views_count')
    actions = ('publish', 'unpublish')

    def save_model(self, request, obj, form, change):
        if not obj.uploaded_by_id:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description='')
    def thumbnail(self, obj):
        if obj.image_src:
            return format_html('<img src="{}" style="width:80px;height:50px;object-fit:cover;border-radius:6px" />', obj.image_src)
        return '-'

    @admin.display(description='پیش‌نمایش')
    def preview(self, obj):
        if obj.image_src:
            return format_html('<img src="{}" style="max-width:320px;border-radius:8px" />', obj.image_src)
        return '-'

    @admin.display(description='تاریخ رویداد', ordering='event_date')
    def event(self, obj):
        return jalali(obj.event_date)

    @admin.action(description='انتشار موارد انتخاب شده')
    def publish(self, request, queryset):
        self.message_user(request, f'{queryset.update(is_published=True)} تصویر منتشر شد.', messages.SUCCESS)

    @admin.action(description='خارج کردن از انتشار')
    def unpublish(self, request, queryset):
        self.message_user(request, f'{queryset.update(is_published=False)} تصویر از انتشار خارج شد.', messages.WARNING)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('short_text', 'author', 'target', 'stars', 'status_badge', 'created')
    list_filter = ('status', 'rating', 'course')
    search_fields = ('author__email', 'author__last_name', 'student__email', 'course__title', 'text')
    autocomplete_fields = ('author', 'student', 'course')
    actions = ('approve_comments', 'reject_comments')
    list_per_page = 30

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('author', 'student', 'course')

    @admin.display(description='متن')
    def short_text(self, obj):
        return obj.text if len(obj.text) <= 60 else obj.text[:60] + '…'

    @admin.display(description='درباره')
    def target(self, obj):
        return obj.course or obj.student or '-'

    @admin.display(description='امتیاز', ordering='rating')
    def stars(self, obj):
        return '★' * obj.rating + '☆' * max(5 - obj.rating, 0)

    @admin.display(description='وضعیت', ordering='status')
    def status_badge(self, obj):
        colors = {'approved': 'green', 'pending': 'orange', 'rejected': 'red'}
        return format_html('<span class="badge badge-{}">{}</span>', colors.get(obj.status, ''), obj.get_status_display())

    @admin.display(description='تاریخ', ordering='created_at')
    def created(self, obj):
        return jalali(obj.created_at)

    @admin.action(description='تایید نظرات انتخاب شده')
    def approve_comments(self, request, queryset):
        self.message_user(request, f'{queryset.update(status=Comment.Status.APPROVED)} نظر تایید شد.', messages.SUCCESS)

    @admin.action(description='رد نظرات انتخاب شده')
    def reject_comments(self, request, queryset):
        self.message_user(request, f'{queryset.update(status=Comment.Status.REJECTED)} نظر رد شد.', messages.WARNING)


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('image_tag', 'title', 'is_active', 'priority', 'start', 'end')
    list_display_links = ('image_tag', 'title')
    list_filter = ('is_active',)
    list_editable = ('is_active', 'priority')
    search_fields = ('title',)

    @admin.display(description='')
    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width:120px;height:50px;object-fit:cover;border-radius:6px" />', obj.image.url)
        return '-'

    @admin.display(description='شروع', ordering='start_date')
    def start(self, obj):
        return jalali(obj.start_date)

    @admin.display(description='پایان', ordering='end_date')
    def end(self, obj):
        return jalali(obj.end_date)


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ('logo_tag', 'title', 'is_active', 'priority')
    list_display_links = ('logo_tag', 'title')
    list_filter = ('is_active',)
    list_editable = ('is_active', 'priority')
    search_fields = ('title',)

    @admin.display(description='')
    def logo_tag(self, obj):
        if obj.logo:
            return format_html('<img src="{}" style="width:90px;height:45px;object-fit:contain" />', obj.logo.url)
        return '-'
