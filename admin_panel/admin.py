from django.contrib import admin, messages
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.decorators import display

from users.admin import jalali
from .models import AdminProfile, Gallery, Comment, Banner, Partner

# JWT token tables are not managed by hand (logout blacklists tokens): keep them out of the panel
try:
    from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
    admin.site.unregister(BlacklistedToken)
    admin.site.unregister(OutstandingToken)
except (ImportError, admin.sites.NotRegistered):
    pass


@admin.register(AdminProfile)
class AdminProfileAdmin(ModelAdmin):
    list_display = ('admin_info', 'level', 'registered')
    list_filter = ('access_level',)
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    autocomplete_fields = ('user',)

    @display(description='ادمین', header=True, ordering='user__last_name')
    def admin_info(self, obj):
        return [obj.user.get_full_name() or obj.user.email, obj.user.email, obj.user.first_name[:1] or '?']

    @display(description='سطح دسترسی', ordering='access_level', label=True)
    def level(self, obj):
        return obj.get_access_level_display()

    @display(description='تاریخ ثبت', ordering='register_datetime')
    def registered(self, obj):
        return jalali(obj.register_datetime, False)


@admin.register(Gallery)
class GalleryAdmin(ModelAdmin):
    list_display = ('thumbnail', 'title', 'is_published', 'event', 'views_count', 'order_index')
    list_display_links = ('thumbnail', 'title')
    list_filter = ('is_published',)
    search_fields = ('title', 'description', 'tags')
    readonly_fields = ('uploaded_at', 'uploaded_by', 'views_count', 'preview')
    list_editable = ('is_published', 'order_index')
    fieldsets = (
        (None, {'fields': ('title', 'description', 'preview', 'image', 'image_url', ('event_date', 'tags'), ('is_published', 'order_index'))}),
        ('اطلاعات آپلود', {'fields': (('uploaded_by', 'uploaded_at'), 'views_count'), 'classes': ('collapse',)}),
    )
    actions = ('publish', 'unpublish')

    def save_model(self, request, obj, form, change):
        if not obj.uploaded_by_id:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)

    @display(description='')
    def thumbnail(self, obj):
        if obj.image_src:
            return format_html('<img src="{}" style="width:84px;height:52px;object-fit:cover;border-radius:8px" />', obj.image_src)
        return '-'

    @display(description='پیش‌نمایش')
    def preview(self, obj):
        if obj.image_src:
            return format_html('<img src="{}" style="max-width:320px;border-radius:10px" />', obj.image_src)
        return '-'

    @display(description='تاریخ رویداد', ordering='event_date')
    def event(self, obj):
        return jalali(obj.event_date)

    @admin.action(description='انتشار موارد انتخاب شده')
    def publish(self, request, queryset):
        self.message_user(request, f'{queryset.update(is_published=True)} تصویر منتشر شد.', messages.SUCCESS)

    @admin.action(description='خارج کردن از انتشار')
    def unpublish(self, request, queryset):
        self.message_user(request, f'{queryset.update(is_published=False)} تصویر از انتشار خارج شد.', messages.WARNING)


@admin.register(Comment)
class CommentAdmin(ModelAdmin):
    list_display = ('short_text', 'author', 'target', 'stars', 'status_label', 'created')
    list_filter = ('status', 'rating', 'course')
    list_filter_submit = True
    search_fields = ('author__email', 'author__last_name', 'student__email', 'course__title', 'text')
    autocomplete_fields = ('author', 'student', 'course')
    actions = ('approve_comments', 'reject_comments')
    list_per_page = 30

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('author', 'student', 'course')

    @display(description='متن')
    def short_text(self, obj):
        return obj.text if len(obj.text) <= 60 else obj.text[:60] + '…'

    @display(description='درباره')
    def target(self, obj):
        return obj.course or obj.student or '-'

    @display(description='امتیاز', ordering='rating')
    def stars(self, obj):
        return format_html('<span style="color:#f59e0b;letter-spacing:1px">{}</span><span style="opacity:.25">{}</span>', '★' * obj.rating, '★' * max(5 - obj.rating, 0))

    @display(description='وضعیت', ordering='status', label={'تایید شده': 'success', 'در انتظار تایید': 'warning', 'رد شده': 'danger'})
    def status_label(self, obj):
        return obj.get_status_display()

    @display(description='تاریخ', ordering='created_at')
    def created(self, obj):
        return jalali(obj.created_at)

    @admin.action(description='تایید نظرات انتخاب شده')
    def approve_comments(self, request, queryset):
        self.message_user(request, f'{queryset.update(status=Comment.Status.APPROVED)} نظر تایید شد.', messages.SUCCESS)

    @admin.action(description='رد نظرات انتخاب شده')
    def reject_comments(self, request, queryset):
        self.message_user(request, f'{queryset.update(status=Comment.Status.REJECTED)} نظر رد شد.', messages.WARNING)


@admin.register(Banner)
class BannerAdmin(ModelAdmin):
    list_display = ('image_tag', 'title', 'is_active', 'priority', 'start', 'end')
    list_display_links = ('image_tag', 'title')
    list_filter = ('is_active',)
    list_editable = ('is_active', 'priority')
    search_fields = ('title',)
    fieldsets = (
        (None, {'fields': ('title', 'image', 'link', ('priority', 'is_active'), ('start_date', 'end_date'))}),
    )

    @display(description='')
    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width:130px;height:52px;object-fit:cover;border-radius:8px" />', obj.image.url)
        return '-'

    @display(description='شروع', ordering='start_date')
    def start(self, obj):
        return jalali(obj.start_date)

    @display(description='پایان', ordering='end_date')
    def end(self, obj):
        return jalali(obj.end_date)


@admin.register(Partner)
class PartnerAdmin(ModelAdmin):
    list_display = ('logo_tag', 'title', 'is_active', 'priority')
    list_display_links = ('logo_tag', 'title')
    list_filter = ('is_active',)
    list_editable = ('is_active', 'priority')
    search_fields = ('title',)

    @display(description='')
    def logo_tag(self, obj):
        if obj.logo:
            return format_html('<img src="{}" style="width:96px;height:48px;object-fit:contain" />', obj.logo.url)
        return '-'
