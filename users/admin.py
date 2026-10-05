import jdatetime
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin, StackedInline, TabularInline
from unfold.contrib.filters.admin import RangeDateFilter
from unfold.decorators import display
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

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
    radius = '9999px' if _round else '8px'
    return format_html('<img src="{}" style="width:{}px;height:{}px;object-fit:cover;border-radius:{}" />', _file.url, _width, _height, radius)


def money(_value):
    if _value is None:
        return '-'
    if not _value:
        return 'رایگان'
    return f"{int(_value):,} تومان"


admin.site.site_title = 'مدیریت البرز'
admin.site.index_title = 'داشبورد'

# Groups use the Unfold look too
admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


# ==================== USER & TEACHER ====================
class TeacherInline(StackedInline):
    model = Teacher
    can_delete = False
    fk_name = 'user'
    fields = ('is_approved', 'education_degree', 'academic_field', 'bio', 'profile_image')
    extra = 0
    tab = True


class InvoiceInline(TabularInline):
    model = Invoice
    fk_name = 'student'
    extra = 0
    fields = ('course', 'amount', 'paid', 'paid_at', 'grade', 'score')
    autocomplete_fields = ('course',)
    verbose_name_plural = 'دوره‌های ثبت‌نام شده'
    tab = True


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
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    list_display = ('user_info', 'phone_number', 'role', 'is_active', 'joined')
    list_filter = (RoleFilter, 'is_active', 'is_staff', 'gender')
    list_filter_submit = True
    search_fields = ('email', 'first_name', 'last_name', 'phone_number', 'national_id')
    readonly_fields = ('last_login', 'date_joined', 'avatar_large')
    ordering = ('-date_joined',)
    list_per_page = 30
    actions = ('activate_users', 'deactivate_users')
    fieldsets = (
        ('حساب کاربری', {'fields': ('email', 'username', 'password')}),
        ('اطلاعات شخصی', {
            'fields': ('avatar_large', 'profile_image', ('first_name', 'last_name'), ('phone_number', 'national_id'),
                       ('birthday_date', 'gender'), ('fathers_name', 'education_level')),
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

    @display(description='کاربر', header=True, ordering='last_name')
    def user_info(self, obj):
        initials = obj.first_name[:1] or obj.email[:1].upper()
        if obj.profile_image:
            return [obj.get_full_name() or obj.email, obj.email, None, {'path': obj.profile_image.url, 'squared': False}]
        return [obj.get_full_name() or obj.email, obj.email, initials]

    @display(description='تصویر')
    def avatar_large(self, obj):
        return image_preview(obj.profile_image, 120, 120, True)

    @display(description='نقش', label={'مدیر کل': 'danger', 'ادمین': 'primary', 'استاد': 'success', 'استاد (در انتظار)': 'warning', 'دانشجو': 'info'})
    def role(self, obj):
        if obj.is_superuser:
            return 'مدیر کل'
        if obj.is_staff or hasattr(obj, 'admin_profile'):
            return 'ادمین'
        if hasattr(obj, 'teacher'):
            return 'استاد' if obj.teacher.is_approved else 'استاد (در انتظار)'
        return 'دانشجو'

    @display(description='عضویت', ordering='date_joined')
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
class TeacherAdmin(ModelAdmin):
    list_display = ('teacher_info', 'academic_field', 'courses_count', 'status', 'is_approved')
    list_filter = ('is_approved', 'academic_field')
    list_filter_submit = True
    list_editable = ('is_approved',)
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'academic_field')
    autocomplete_fields = ('user',)
    actions = ('approve', 'unapprove')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user').annotate(_courses=Count('courses'))

    @display(description='استاد', header=True, ordering='user__last_name')
    def teacher_info(self, obj):
        image = obj.profile_image or obj.user.profile_image
        if image:
            return [obj.user.get_full_name(), obj.user.email, None, {'path': image.url, 'squared': False}]
        return [obj.user.get_full_name(), obj.user.email, obj.user.first_name[:1] or '?']

    @display(description='تعداد دوره', ordering='_courses')
    def courses_count(self, obj):
        return obj._courses

    @display(description='وضعیت', label={'تایید شده': 'success', 'در انتظار تایید': 'warning'})
    def status(self, obj):
        return 'تایید شده' if obj.is_approved else 'در انتظار تایید'

    @admin.action(description='تایید اساتید انتخاب شده')
    def approve(self, request, queryset):
        count = queryset.update(is_approved=True)
        self.message_user(request, f'{count} استاد تایید شد.', messages.SUCCESS)

    @admin.action(description='لغو تایید اساتید انتخاب شده')
    def unapprove(self, request, queryset):
        count = queryset.update(is_approved=False)
        self.message_user(request, f'تایید {count} استاد لغو شد.', messages.WARNING)


# ==================== COURSE & SESSIONS ====================
class CourseSessionInline(TabularInline):
    model = CourseSession
    extra = 0
    fields = ('order', 'title', 'is_free', 'video', 'pdf')
    ordering = ('order', 'id')
    tab = True


@admin.register(Course)
class CourseAdmin(ModelAdmin):
    list_display = ('course_info', 'teacher', 'price', 'students_count', 'sessions_count', 'start', 'status', 'is_active')
    list_filter = ('is_active', 'category', 'level', 'teacher', ('start_date', RangeDateFilter))
    list_filter_submit = True
    list_editable = ('is_active',)
    search_fields = ('title', 'description', 'tags', 'teacher__user__first_name', 'teacher__user__last_name')
    readonly_fields = ('created_at', 'last_updated', 'rating_avg', 'cover_large')
    autocomplete_fields = ('teacher',)
    inlines = [CourseSessionInline]
    list_per_page = 25
    actions = ('activate', 'deactivate')
    warn_unsaved_form = True

    fieldsets = (
        ('اطلاعات اصلی', {'fields': ('title', 'teacher', ('category', 'level'), 'tags', 'cover_large', 'logo')}),
        ('توضیحات', {'fields': ('short_description', 'description', 'requirements')}),
        ('قیمت و ظرفیت', {'fields': (('cost', 'discount_price'), 'limit_students')}),
        ('زمان‌بندی', {'fields': (('start_date', 'end_date'), ('exam_date', 'duration'))}),
        ('وضعیت', {'fields': ('is_active', 'rating_avg', ('created_at', 'last_updated'))}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('teacher__user').annotate(
            _students=Count('invoices', filter=Q(invoices__paid=True), distinct=True),
            _sessions=Count('sessions', distinct=True),
        )

    @display(description='دوره', header=True, ordering='title')
    def course_info(self, obj):
        subtitle = ' · '.join(filter(None, [obj.category, obj.level])) or '-'
        if obj.logo:
            return [obj.title, subtitle, None, {'path': obj.logo.url, 'squared': True}]
        return [obj.title, subtitle, obj.title[:1]]

    @display(description='تصویر فعلی')
    def cover_large(self, obj):
        return image_preview(obj.logo, 240, 140)

    @display(description='قیمت', ordering='cost')
    def price(self, obj):
        if obj.discount_price is not None and obj.cost and obj.discount_price < obj.cost:
            return format_html('<s style="opacity:.55">{}</s><br><strong>{}</strong>', money(obj.cost), money(obj.discount_price))
        return money(obj.cost or 0)

    @display(description='دانشجو', ordering='_students')
    def students_count(self, obj):
        if obj.limit_students:
            return f'{obj._students} / {obj.limit_students}'
        return obj._students

    @display(description='جلسات', ordering='_sessions')
    def sessions_count(self, obj):
        return obj._sessions

    @display(description='شروع', ordering='start_date')
    def start(self, obj):
        return jalali(obj.start_date)

    @display(description='وضعیت', label={'فعال': 'success', 'غیرفعال': 'danger', 'تکمیل ظرفیت': 'warning'})
    def status(self, obj):
        if not obj.is_active:
            return 'غیرفعال'
        if obj.limit_students and obj._students >= obj.limit_students:
            return 'تکمیل ظرفیت'
        return 'فعال'

    @admin.action(description='فعال کردن دوره‌های انتخاب شده')
    def activate(self, request, queryset):
        self.message_user(request, f'{queryset.update(is_active=True)} دوره فعال شد.', messages.SUCCESS)

    @admin.action(description='غیرفعال کردن دوره‌های انتخاب شده')
    def deactivate(self, request, queryset):
        self.message_user(request, f'{queryset.update(is_active=False)} دوره غیرفعال شد.', messages.WARNING)


@admin.register(CourseSession)
class CourseSessionAdmin(ModelAdmin):
    list_display = ('title', 'course_link', 'order', 'is_free', 'has_video', 'has_pdf', 'created')
    list_filter = ('is_free', 'course')
    list_filter_submit = True
    list_editable = ('order', 'is_free')
    search_fields = ('title', 'course__title')
    autocomplete_fields = ('course',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('course')

    @display(description='دوره', ordering='course__title')
    def course_link(self, obj):
        url = reverse('admin:users_course_change', args=[obj.course_id])
        return format_html('<a href="{}" class="text-primary-600">{}</a>', url, obj.course.title)

    @display(description='ویدیو', boolean=True)
    def has_video(self, obj):
        return bool(obj.video)

    @display(description='جزوه', boolean=True)
    def has_pdf(self, obj):
        return bool(obj.pdf)

    @display(description='تاریخ', ordering='created_at')
    def created(self, obj):
        return jalali(obj.created_at, False)


# ==================== INVOICE (enrollment) ====================
@admin.register(Invoice)
class InvoiceAdmin(ModelAdmin):
    list_display = ('id', 'student_info', 'course', 'amount_display', 'payment_status', 'date', 'paid_date', 'score')
    list_display_links = ('id', 'student_info')
    list_filter = ('paid', 'course', ('date_time', RangeDateFilter))
    list_filter_submit = True
    search_fields = ('student__email', 'student__first_name', 'student__last_name', 'student__phone_number', 'course__title')
    readonly_fields = ('date_time',)
    autocomplete_fields = ('student', 'course')
    actions = ('mark_paid', 'mark_unpaid')
    list_per_page = 30
    fieldsets = (
        (None, {'fields': (('student', 'course'), ('amount', 'paid'), 'paid_at', ('grade', 'score'), 'date_time')}),
    )

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

    @display(description='دانشجو', header=True, ordering='student__last_name')
    def student_info(self, obj):
        return [obj.student.get_full_name() or obj.student.email, obj.student.email, obj.student.first_name[:1] or '?']

    @display(description='مبلغ', ordering='amount')
    def amount_display(self, obj):
        return money(obj.amount)

    @display(description='وضعیت', ordering='paid', label={'پرداخت شده': 'success', 'در انتظار پرداخت': 'warning'})
    def payment_status(self, obj):
        return 'پرداخت شده' if obj.paid else 'در انتظار پرداخت'

    @display(description='ثبت‌نام', ordering='date_time')
    def date(self, obj):
        return jalali(obj.date_time)

    @display(description='پرداخت', ordering='paid_at')
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
