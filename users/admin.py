# admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, Teacher, Course, CourseSession, Invoice
from admin_panel.models import AdminProfile, Gallery, Comment, Banner, Partner


# ==================== USER & TEACHER ====================
class TeacherInline(admin.StackedInline):
    model = Teacher
    can_delete = False
    verbose_name_plural = 'Teacher Profile'
    fk_name = 'user'
    fields = ('education_degree', 'academic_field', 'bio', 'profile_image')
    extra = 0


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_teacher', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'national_id')
    readonly_fields = ('last_login', 'date_joined')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'email', 'birthday_date', 'national_id',
                       'gender', 'fathers_name', 'education_level', 'profile_image')
        }),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )
    inlines = [TeacherInline]

    def is_teacher(self, obj):
        return hasattr(obj, 'teacher')
    is_teacher.boolean = True
    is_teacher.short_description = 'Is Teacher?'


# ==================== COURSE & SESSIONS ====================
class CourseSessionInline(admin.TabularInline):
    model = CourseSession
    extra = 0
    fields = ('title', 'video', 'pdf', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'teacher', 'cost', 'discount_price', 'is_active', 'students_count', 'created_at')
    list_filter = ('is_active', 'category', 'level', 'teacher', 'created_at')
    search_fields = ('title', 'description', 'teacher__user__first_name', 'teacher__user__last_name')
    readonly_fields = ('created_at', 'last_updated', 'rating_avg')
    prepopulated_fields = {"logo": ("title",)}  
    inlines = [CourseSessionInline]
    filter_horizontal = ()

    fieldsets = (
        ('Main Info', {
            'fields': ('title', 'teacher', 'category', 'level', 'tags', 'logo')
        }),
        ('Description', {
            'fields': ('short_description', 'description', 'requirements'),
            'classes': ('collapse',)
        }),
        ('Pricing & Dates', {
            'fields': ('cost', 'discount_price', 'start_date', 'end_date', 'exam_date', 'duration', 'limit_students')
        }),
        ('Status', {
            'fields': ('is_active', 'rating_avg', 'created_at', 'last_updated')
        }),
    )

    def students_count(self, obj):
        return obj.invoices.filter(paid=True).count()
    students_count.short_description = 'Enrolled Students'


@admin.register(CourseSession)
class CourseSessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'course_link', 'has_video', 'has_pdf', 'created_at')
    list_filter = ('course__title', 'created_at')
    search_fields = ('title', 'course__title')

    def course_link(self, obj):
        return format_html('<a href="{}">{}</a>', 
                             f"/admin/your_app_name/course/{obj.course.id}/change/", 
                             obj.course.title)
    course_link.short_description = 'Course'

    def has_video(self, obj):
        return bool(obj.video)
    has_video.boolean = True

    def has_pdf(self, obj):
        return bool(obj.pdf)
    has_pdf.boolean = True


# ==================== INVOICE (Enrollment) ====================
@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'course', 'paid', 'grade', 'score', 'date_time')
    list_filter = ('paid', 'course', 'date_time')
    search_fields = ('student__email', 'student__username', 'course__title')
    readonly_fields = ('date_time',)
    raw_id_fields = ('student', 'course')  


# ==================== ADMIN PROFILE ====================
@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'access_level_display', 'register_datetime')
    list_filter = ('access_level', 'register_datetime')
    search_fields = ('user__username', 'user__email')

    def access_level_display(self, obj):
        return obj.get_access_level_display()
    access_level_display.short_description = 'Access Level'


# ==================== GALLERY ====================
@admin.register(Gallery)
class GalleryAdmin(admin.ModelAdmin):
    list_display = ('title', 'thumbnail', 'is_published', 'event_date', 'uploaded_by', 'views_count', "order_index")
    list_filter = ('is_published', 'event_date', 'uploaded_by')
    search_fields = ('title', 'description', 'tags')
    readonly_fields = ('uploaded_at', 'views_count')
    list_editable = ('is_published', 'order_index')

    def thumbnail(self, obj):
        if obj.image_url:
            return format_html('<img src="{}" width="80" height="50" style="object-fit: cover; border-radius: 4px;" />', obj.image_url)
        return "No Image"
    thumbnail.short_description = 'Preview'


# ==================== COMMENT ====================
@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'student', 'rating', 'status', 'created_at')
    list_filter = ('status', 'rating', 'created_at')
    search_fields = ('author__username', 'student__username', 'text')
    actions = ['approve_comments', 'reject_comments']

    def approve_comments(self, request, queryset):
        queryset.update(status='approved')
    approve_comments.short_description = "Approve selected comments"

    def reject_comments(self, request, queryset):
        queryset.update(status='rejected')
    reject_comments.short_description = "Reject selected comments"


# ==================== BANNER ====================
@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'image_tag', 'is_active', 'priority', 'start_date', 'end_date')
    list_filter = ('is_active', 'start_date', 'end_date')
    list_editable = ('is_active', 'priority')

    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="120" height="60" />', obj.image.url)
        return "No Image"
    image_tag.short_description = 'Image'


# ==================== PARTNER ====================
@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ('title', 'logo_tag', 'is_active', 'priority')
    list_filter = ('is_active', 'priority')
    list_editable = ('is_active', 'priority')

    def logo_tag(self, obj):
        if obj.logo:
            return format_html('<img src="{}" width="100" height="50" style="object-fit: contain;" />', obj.logo.url)
        return "No Logo"
    logo_tag.short_description = 'Logo'



admin.site.site_header = "Educational Platform Administration"
admin.site.site_title = "EduAdmin"
admin.site.index_title = "Welcome to the Admin Panel"