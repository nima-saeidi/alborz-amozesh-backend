"""
Admin theme (django-unfold): Alborz blue, Persian RTL sidebar, dashboard numbers.
Icons are Material Symbols names: https://fonts.google.com/icons
"""
from datetime import timedelta

from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils import timezone


def _count(model_path, **filters):
    from django.apps import apps
    return apps.get_model(model_path).objects.filter(**filters).count()


# -------------------- Sidebar badges (pending work) --------------------
def badge_unpaid_invoices(request):
    return _count('users.Invoice', paid=False) or None


def badge_pending_teachers(request):
    return _count('users.Teacher', is_approved=False) or None


def badge_pending_comments(request):
    return _count('admin_panel.Comment', status='pending') or None


def _can(permission):
    return lambda request: request.user.is_superuser or request.user.has_perm(permission)


# -------------------- Dashboard --------------------
def dashboard_callback(request, context):
    from django.db.models import Count, Q, Sum
    from users.models import User, Teacher, Course, Invoice
    from admin_panel.models import Comment

    now = timezone.now()
    month_ago = now - timedelta(days=30)
    paid = Invoice.objects.filter(paid=True)
    revenue = paid.aggregate(total=Sum('amount'))['total'] or 0
    revenue_month = paid.filter(paid_at__gte=month_ago).aggregate(total=Sum('amount'))['total'] or 0

    # Paid enrollments per day for the last 14 days (small bar chart)
    days = []
    for offset in range(13, -1, -1):
        day = (now - timedelta(days=offset)).date()
        days.append({'day': day, 'count': Invoice.objects.filter(date_time__date=day).count()})
    peak = max([d['count'] for d in days] + [1])
    for d in days:
        d['height'] = max(4, round(d['count'] / peak * 100))

    context.update({
        'dashboard': {
            'cards': [
                {'title': 'دانشجویان', 'value': User.objects.filter(teacher__isnull=True, is_staff=False).count(), 'note': f"{User.objects.filter(date_joined__gte=month_ago).count()} کاربر جدید در ۳۰ روز اخیر", 'icon': 'school', 'link': reverse_lazy('admin:users_user_changelist') + '?role=student'},
                {'title': 'اساتید', 'value': Teacher.objects.filter(is_approved=True).count(), 'note': (f"{badge_pending_teachers(request)} استاد در انتظار تایید" if badge_pending_teachers(request) else 'همه تایید شده‌اند'), 'icon': 'person_book', 'link': reverse_lazy('admin:users_teacher_changelist'), 'warn': bool(badge_pending_teachers(request))},
                {'title': 'دوره‌های فعال', 'value': Course.objects.filter(is_active=True).count(), 'note': f"{Course.objects.count()} دوره در مجموع", 'icon': 'menu_book', 'link': reverse_lazy('admin:users_course_changelist')},
                {'title': 'فاکتورهای پرداخت‌نشده', 'value': Invoice.objects.filter(paid=False).count(), 'note': 'ثبت پرداخت از فهرست فاکتورها', 'icon': 'receipt_long', 'link': reverse_lazy('admin:users_invoice_changelist') + '?paid__exact=0', 'warn': bool(badge_unpaid_invoices(request))},
            ],
            'revenue': f"{int(revenue):,}",
            'revenue_month': f"{int(revenue_month):,}",
            'pending_comments': Comment.objects.filter(status='pending').count(),
            'days': days,
            'recent_invoices': Invoice.objects.select_related('student', 'course').order_by('-date_time')[:6],
            'top_courses': Course.objects.annotate(students=Count('invoices', filter=Q(invoices__paid=True))).order_by('-students', '-created_at')[:5],
            'quick_links': [
                {'title': 'دوره جدید', 'icon': 'add_circle', 'link': reverse_lazy('admin:users_course_add')},
                {'title': 'ثبت‌نام دستی', 'icon': 'how_to_reg', 'link': reverse_lazy('admin:users_invoice_add')},
                {'title': 'بنر جدید', 'icon': 'imagesmode', 'link': reverse_lazy('admin:admin_panel_banner_add')},
                {'title': 'بررسی نظرات', 'icon': 'rate_review', 'link': reverse_lazy('admin:admin_panel_comment_changelist') + '?status__exact=pending'},
            ],
        },
    })
    return context


UNFOLD = {
    'SITE_TITLE': 'مدیریت البرز',
    'SITE_HEADER': 'آموزشگاه البرز',
    'SITE_SUBHEADER': 'پنل مدیریت',
    'SITE_URL': '/',
    'SITE_SYMBOL': 'school',
    'SITE_ICON': lambda request: static('admin_custom/logo.svg'),
    'SITE_FAVICONS': [
        {'rel': 'icon', 'sizes': 'any', 'type': 'image/svg+xml', 'href': lambda request: static('admin_custom/logo.svg')},
    ],
    'SHOW_HISTORY': True,
    'SHOW_VIEW_ON_SITE': False,
    'SHOW_BACK_BUTTON': True,
    'DASHBOARD_CALLBACK': 'config.unfold.dashboard_callback',
    'STYLES': [
        lambda request: static('admin_custom/unfold.css'),
    ],
    'COLORS': {
        'primary': {
            '50': '#eef4ff',
            '100': '#dce7ff',
            '200': '#b9cfff',
            '300': '#8ab0ff',
            '400': '#5687ff',
            '500': '#2f63ff',
            '600': '#1a47f0',
            '700': '#1338c9',
            '800': '#13319f',
            '900': '#142c7d',
            '950': '#0b1a4d',
        },
    },
    'LOGIN': {
        'image': lambda request: static('admin_custom/login.svg'),
    },
    'SIDEBAR': {
        'show_search': True,
        'show_all_applications': False,
        'navigation': [
            {
                'title': 'عمومی',
                'items': [
                    {'title': 'داشبورد', 'icon': 'dashboard', 'link': reverse_lazy('admin:index')},
                ],
            },
            {
                'title': 'آموزش',
                'separator': True,
                'items': [
                    {'title': 'دوره‌ها', 'icon': 'menu_book', 'link': reverse_lazy('admin:users_course_changelist'), 'permission': _can('users.view_course')},
                    {'title': 'جلسات', 'icon': 'play_lesson', 'link': reverse_lazy('admin:users_coursesession_changelist'), 'permission': _can('users.view_coursesession')},
                    {'title': 'ثبت‌نام‌ها و فاکتورها', 'icon': 'receipt_long', 'link': reverse_lazy('admin:users_invoice_changelist'), 'badge': 'config.unfold.badge_unpaid_invoices', 'permission': _can('users.view_invoice')},
                    {'title': 'اساتید', 'icon': 'person_book', 'link': reverse_lazy('admin:users_teacher_changelist'), 'badge': 'config.unfold.badge_pending_teachers', 'permission': _can('users.view_teacher')},
                ],
            },
            {
                'title': 'کاربران',
                'separator': True,
                'items': [
                    {'title': 'همه کاربران', 'icon': 'group', 'link': reverse_lazy('admin:users_user_changelist'), 'permission': _can('users.view_user')},
                    {'title': 'ادمین‌ها', 'icon': 'admin_panel_settings', 'link': reverse_lazy('admin:admin_panel_adminprofile_changelist'), 'permission': _can('admin_panel.view_adminprofile')},
                    {'title': 'گروه‌های دسترسی', 'icon': 'shield_person', 'link': reverse_lazy('admin:auth_group_changelist'), 'permission': _can('auth.view_group')},
                ],
            },
            {
                'title': 'محتوای سایت',
                'separator': True,
                'items': [
                    {'title': 'بنرها', 'icon': 'imagesmode', 'link': reverse_lazy('admin:admin_panel_banner_changelist'), 'permission': _can('admin_panel.view_banner')},
                    {'title': 'گالری', 'icon': 'photo_library', 'link': reverse_lazy('admin:admin_panel_gallery_changelist'), 'permission': _can('admin_panel.view_gallery')},
                    {'title': 'همکاران', 'icon': 'handshake', 'link': reverse_lazy('admin:admin_panel_partner_changelist'), 'permission': _can('admin_panel.view_partner')},
                    {'title': 'نظرات', 'icon': 'rate_review', 'link': reverse_lazy('admin:admin_panel_comment_changelist'), 'badge': 'config.unfold.badge_pending_comments', 'permission': _can('admin_panel.view_comment')},
                ],
            },
        ],
    },
}
