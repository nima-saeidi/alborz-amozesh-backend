from datetime import timedelta

import jdatetime
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Count, Q, Sum
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import User, Teacher, Course, CourseSession, Invoice


# ==================== HELPERS ====================
def jalali(_value, _with_time=True):
    """Display a date / datetime in the Jalali calendar"""
    if not _value:
        return '-'
    if hasattr(_value, 'hour'):
        _value = timezone.localtime(_value) if timezone.is_aware(_value) else _value
        converted = jdatetime.datetime.fromgregorian(datetime=_value)
        return converted.strftime('%Y/%m/%d %H:%M' if _with_time else '%Y/%m/%d')
    return jdatetime.date.fromgregorian(date=_value).strftime('%Y/%m/%d')


def image_preview(_file, _width=60, _height=60, _round=False):
    if not _file:
        return '-'
    radius = '50%' if _round else '6px'
    return format_html('<img src="{}" style="width:{}px;height:{}px;object-fit:cover;border-radius:{}" />', _file.url, _width, _height, radius)


def money(_value):
    if _value is None:
        return '-'
    return f"{int(_value):,} تومان"


def dashboard_stats():
    now = timezone.now()
    month_ago = now - timedelta(days=30)
    from admin_panel.models import Comment
    paid = Invoice.objects.filter(paid=True)
    return {
        'students': User.objects.filter(teacher__isnull=True, is_staff=False).count(),
        'new_users': User.objects.filter(date_joined__gte=month_ago).count(),
        'teachers': Teacher.objects.filter(is_approved=True).count(),
        'pending_teachers': Teacher.objects.filter(is_approved=False).count(),
        'courses': Course.objects.filter(is_active=True).count(),
        'unpaid_invoices': Invoice.objects.filter(paid=False).count(),
        'revenue': money(paid.aggregate(total=Sum('amount'))['total'] or 0),
        'revenue_month': money(paid.filter(paid_at__gte=month_ago).aggregate(total=Sum('amount'))['total'] or 0),
        'pending_comments': Comment.objects.filter(status='pending').count(),
        'recent_invoices': Invoice.objects.select_related('student', 'course').order_by('-date_time')[:8],
        'top_courses': Course.objects.annotate(students=Count('invoices', filter=Q(invoices__paid=True))).order_by('-students')[:5],
    }


# Statistics on the admin home page (templates/admin/index.html)
_original_index = admin.site.index


def _index_with_dashboard(request, extra_context=None):
    extra_context = {**(extra_context or {}), 'dashboard': dashboard_stats()}
    return _original_index(request, extra_context)


admin.site.index = _index_with_dashboard
admin.site.site_header = 'پنل مدیریت آموزشگاه البرز'
admin.site.site_title = 'مدیریت البرز'
admin.site.index_title = 'داشبورد'


# ==================== USER & TEACHER ====================
class TeacherInline(admin.StackedInline):
    model = Teacher
    can_delete = False
    fk_name = 'user'
    fields = ('is_approved', 'education_degree', 'academic_field', 'bio', 'profile_image')
    extra = 0


class InvoiceInline(admin.TabularInline):
    model = Invoice
    fk_name = 'student'
    extra = 0
    fields = ('course', 'amount', 'paid', 'paid_at', 'grade', 'score')
    autocomplete_fields = ('course',)
    verbose_name_plural = 'دوره‌های ثبت‌نام شده'


class RoleFilter(admin.SimpleListFilter):
    title = 'نقش'
    parameter_name = 'role'

    def lookups(self, request, model_admin):
        return [('student', 'دانشجو'), ('teacher', 'استاد'), ('pending_teacher', 'استاد در انتظار تایید'), ('admin', 'ادمین')]

    def queryset(self, request, queryset):
        value = self.value()
        if value == 'student':
            return queryset.filter(teacher__isnull=True, is_staff=False)
        if value == 'teacher':
            return queryset.filter(teacher__is_approved=True)
        if value == 'pending_teacher':
            return queryset.filter(teacher__is_approved=False)
        if value == 'admin':
            return queryset.filter(Q(is_staff=True) | Q(admin_profile__isnull=False))
        return queryset


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('avatar', 'full_name', 'email', 'phone_number', 'role', 'is_active', 'joined')
    list_display_links = ('avatar', 'full_name')
    list_filter = (RoleFilter, 'is_active', 'is_staff', 'gender')
    search_fields = ('email', 'first_name', 'last_name', 'phone_number', 'national_id')
    readonly_fields = ('last_login', 'date_joined', 'avatar_large')
    ordering = ('-date_joined',)
    list_per_page = 30
    actions = ('activate_users', 'deactivate_users')
    fieldsets = (
        ('حساب کاربری', {'fields': ('email', 'username', 'password')}),
        ('اطلاعات شخصی', {
            'fields': ('avatar_large', 'profile_image', 'first_name', 'last_name', 'phone_number', 'national_id',
                       'birthday_date', 'gender', 'fathers_name', 'education_level')
        }),
        ('دسترسی‌ها', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'), 'classes': ('collapse',)}),
        ('تاریخ‌ها', {'fields': ('last_login', 'date_joined'), 'classes': ('collapse',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )
    inlines = [TeacherInline, InvoiceInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('teacher', 'admin_profile')

    @admin.display(description='')
    def avatar(self, obj):
        return image_preview(obj.profile_image, 36, 36, True)

    @admin.display(description='تصویر')
    def avatar_large(self, obj):
        return image_preview(obj.profile_image, 120, 120, True)

    @admin.display(description='نام', ordering='last_name')
    def full_name(self, obj):
        return obj.get_full_name() or '-'

    @admin.display(description='نقش')
    def role(self, obj):
        if obj.is_superuser:
            return format_html('<span class="badge badge-dark">{}</span>', 'مدیر کل')
        if obj.is_staff or hasattr(obj, 'admin_profile'):
            return format_html('<span class="badge badge-blue">{}</span>', 'ادمین')
        if hasattr(obj, 'teacher'):
            if obj.teacher.is_approved:
                return format_html('<span class="badge badge-green">{}</span>', 'استاد')
            return format_html('<span class="badge badge-orange">{}</span>', 'استاد (در انتظار)')
        return format_html('<span class="badge">{}</span>', 'دانشجو')

    @admin.display(description='عضویت', ordering='date_joined')
    def joined(self, obj):
        return jalali(obj.date_joined, False)

    @admin.action(description='فعال کردن کاربران انتخاب شده')
    def activate_users(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} کاربر فعال شد.', messages.SUCCESS)

    @admin.action(description='غیرفعال کردن کاربران انتخاب شده')
    def deactivate_users(self, request, queryset):
        count = queryset.exclude(pk=request.user.pk).update(is_active=False)
        self.message_user(request, f'{count} کاربر غیرفعال شد.', messages.WARNING)


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('photo', 'name', 'email', 'academic_field', 'courses_count', 'is_approved')
    list_display_links = ('photo', 'name')
    list_filter = ('is_approved', 'academic_field')
    list_editable = ('is_approved',)
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'academic_field')
    autocomplete_fields = ('user',)
    actions = ('approve', 'unapprove')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user').annotate(_courses=Count('courses'))

    @admin.display(description='')
    def photo(self, obj):
        return image_preview(obj.profile_image or obj.user.profile_image, 40, 40, True)

    @admin.display(description='نام', ordering='user__last_name')
    def name(self, obj):
        return obj.user.get_full_name()

    @admin.display(description='ایمیل', ordering='user__email')
    def email(self, obj):
        return obj.user.email

    @admin.display(description='تعداد دوره', ordering='_courses')
    def courses_count(self, obj):
        return obj._courses

    @admin.action(description='تایید اساتید انتخاب شده')
    def approve(self, request, queryset):
        count = queryset.update(is_approved=True)
        self.message_user(request, f'{count} استاد تایید شد.', messages.SUCCESS)

    @admin.action(description='لغو تایید اساتید انتخاب شده')
    def unapprove(self, request, queryset):
        count = queryset.update(is_approved=False)
        self.message_user(request, f'تایید {count} استاد لغو شد.', messages.WARNING)


# ==================== COURSE & SESSIONS ====================
class CourseSessionInline(admin.TabularInline):
    model = CourseSession
    extra = 0
    fields = ('order', 'title', 'is_free', 'video', 'pdf')
    ordering = ('order', 'id')


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('cover', 'title', 'teacher', 'category', 'price', 'students_count', 'sessions_count', 'start', 'is_active')
    list_display_links = ('cover', 'title')
    list_filter = ('is_active', 'category', 'level', 'teacher')
    list_editable = ('is_active',)
    search_fields = ('title', 'description', 'tags', 'teacher__user__first_name', 'teacher__user__last_name')
    readonly_fields = ('created_at', 'last_updated', 'rating_avg', 'cover_large')
    autocomplete_fields = ('teacher',)
    inlines = [CourseSessionInline]
    list_per_page = 25
    actions = ('activate', 'deactivate')

    fieldsets = (
        ('اطلاعات اصلی', {'fields': ('title', 'teacher', 'category', 'level', 'tags', 'cover_large', 'logo')}),
        ('توضیحات', {'fields': ('short_description', 'description', 'requirements')}),
        ('قیمت و ظرفیت', {'fields': ('cost', 'discount_price', 'limit_students')}),
        ('زمان‌بندی', {'fields': ('start_date', 'end_date', 'exam_date', 'duration')}),
        ('وضعیت', {'fields': ('is_active', 'rating_avg', 'created_at', 'last_updated')}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('teacher__user').annotate(
            _students=Count('invoices', filter=Q(invoices__paid=True), distinct=True),
            _sessions=Count('sessions', distinct=True),
        )

    @admin.display(description='')
    def cover(self, obj):
        return image_preview(obj.logo, 56, 40)

    @admin.display(description='تصویر فعلی')
    def cover_large(self, obj):
        return image_preview(obj.logo, 240, 140)

    @admin.display(description='قیمت', ordering='cost')
    def price(self, obj):
        if obj.discount_price is not None and obj.cost and obj.discount_price < obj.cost:
            return format_html('<s style="color:#999">{}</s><br>{}', money(obj.cost), money(obj.discount_price))
        return money(obj.cost) if obj.cost else 'رایگان'

    @admin.display(description='دانشجو', ordering='_students')
    def students_count(self, obj):
        if obj.limit_students:
            return f'{obj._students} / {obj.limit_students}'
        return obj._students

    @admin.display(description='جلسات', ordering='_sessions')
    def sessions_count(self, obj):
        return obj._sessions

    @admin.display(description='شروع', ordering='start_date')
    def start(self, obj):
        return jalali(obj.start_date)

    @admin.action(description='فعال کردن دوره‌های انتخاب شده')
    def activate(self, request, queryset):
        self.message_user(request, f'{queryset.update(is_active=True)} دوره فعال شد.', messages.SUCCESS)

    @admin.action(description='غیرفعال کردن دوره‌های انتخاب شده')
    def deactivate(self, request, queryset):
        self.message_user(request, f'{queryset.update(is_active=False)} دوره غیرفعال شد.', messages.WARNING)


@admin.register(CourseSession)
class CourseSessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'course_link', 'order', 'is_free', 'has_video', 'has_pdf', 'created')
    list_filter = ('is_free', 'course')
    list_editable = ('order', 'is_free')
    search_fields = ('title', 'course__title')
    autocomplete_fields = ('course',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('course')

    @admin.display(description='دوره', ordering='course__title')
    def course_link(self, obj):
        url = reverse('admin:users_course_change', args=[obj.course_id])
        return format_html('<a href="{}">{}</a>', url, obj.course.title)

    @admin.display(description='ویدیو', boolean=True)
    def has_video(self, obj):
        return bool(obj.video)

    @admin.display(description='جزوه', boolean=True)
    def has_pdf(self, obj):
        return bool(obj.pdf)

    @admin.display(description='تاریخ', ordering='created_at')
    def created(self, obj):
        return jalali(obj.created_at, False)


# ==================== INVOICE (enrollment) ====================
@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'course', 'amount_display', 'payment_status', 'date', 'paid_date', 'score')
    list_display_links = ('id', 'student')
    list_filter = ('paid', 'course')
    search_fields = ('student__email', 'student__first_name', 'student__last_name', 'student__phone_number', 'course__title')
    readonly_fields = ('date_time',)
    autocomplete_fields = ('student', 'course')
    date_hierarchy = 'date_time'
    actions = ('mark_paid', 'mark_unpaid')
    list_per_page = 30

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('student', 'course')

    def save_model(self, request, obj, form, change):
        if obj.amount is None:
            obj.amount = obj.course.final_price
        if obj.paid and not obj.paid_at:
            obj.paid_at = timezone.now()
        if not obj.paid:
            obj.paid_at = None
        super().save_model(request, obj, form, change)

    @admin.display(description='مبلغ', ordering='amount')
    def amount_display(self, obj):
        return money(obj.amount)

    @admin.display(description='وضعیت', ordering='paid')
    def payment_status(self, obj):
        if obj.paid:
            return format_html('<span class="badge badge-green">{}</span>', 'پرداخت شده')
        return format_html('<span class="badge badge-orange">{}</span>', 'در انتظار پرداخت')

    @admin.display(description='ثبت‌نام', ordering='date_time')
    def date(self, obj):
        return jalali(obj.date_time)

    @admin.display(description='پرداخت', ordering='paid_at')
    def paid_date(self, obj):
        return jalali(obj.paid_at)

    @admin.action(description='ثبت پرداخت برای موارد انتخاب شده')
    def mark_paid(self, request, queryset):
        count = 0
        for invoice in queryset.filter(paid=False).select_related('course'):
            invoice.paid = True
            invoice.paid_at = timezone.now()
            if invoice.amount is None:
                invoice.amount = invoice.course.final_price
            invoice.save(update_fields=['paid', 'paid_at', 'amount'])
            count += 1
        self.message_user(request, f'{count} فاکتور پرداخت شده ثبت شد.', messages.SUCCESS)

    @admin.action(description='برگرداندن به حالت پرداخت نشده')
    def mark_unpaid(self, request, queryset):
        count = queryset.update(paid=False, paid_at=None)
        self.message_user(request, f'{count} فاکتور پرداخت نشده شد.', messages.WARNING)
