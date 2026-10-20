import csv

from django.contrib import admin, messages
from django.http import HttpResponse
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action, display

from users.admin import jalali
from .models import Certificate, ContactMessage, NewsletterSubscriber, Notification, Ticket, TicketMessage


# -------------------- TICKETS --------------------
class TicketMessageInline(TabularInline):
    model = TicketMessage
    extra = 1
    fields = ('sender', 'text', 'attachment', 'sent')
    readonly_fields = ('sender', 'sent')
    verbose_name = 'پیام'
    verbose_name_plural = 'گفتگو (برای پاسخ، در ردیف خالی بنویسید و ذخیره کنید)'

    def has_delete_permission(self, request, obj=None):
        return False

    @display(description='فرستنده')
    def sender(self, obj):
        if not obj.pk:
            return 'پاسخ شما'
        return 'پشتیبانی' if obj.is_staff_reply else (obj.author.get_full_name() if obj.author else '-')

    @display(description='زمان')
    def sent(self, obj):
        return jalali(obj.created_at) if obj.pk else '-'


@admin.register(Ticket)
class TicketAdmin(ModelAdmin):
    list_display = ('ticket_info', 'user_name', 'department', 'status_label', 'updated')
    list_filter = ('status', 'department')
    list_filter_submit = True
    search_fields = ('subject', 'user__first_name', 'user__last_name', 'user__username', 'user__phone_number', 'messages__text')
    readonly_fields = ('user', 'created_at', 'updated_at')
    fields = ('subject', ('user', 'course'), ('department', 'status'), ('created_at', 'updated_at'))
    inlines = [TicketMessageInline]
    actions = ('close_tickets',)
    list_per_page = 30

    def has_add_permission(self, request):
        return False  # tickets are opened by users from the site

    def save_formset(self, request, form, formset, change):
        replies = formset.save(commit=False)
        for reply in replies:
            if not reply.pk:
                reply.author = request.user
                reply.is_staff_reply = True
            reply.save()
        formset.save_m2m()

    @display(description='تیکت', header=True)
    def ticket_info(self, obj):
        return [f'#{obj.id} {obj.subject}', obj.course.title if obj.course else obj.get_department_display()]

    @display(description='کاربر', ordering='user__last_name')
    def user_name(self, obj):
        return obj.user.get_full_name() or obj.user.contact

    @display(description='وضعیت', ordering='status', label={'در انتظار پاسخ': 'warning', 'پاسخ داده شده': 'success', 'بسته شده': 'info'})
    def status_label(self, obj):
        return obj.get_status_display()

    @display(description='آخرین تغییر', ordering='updated_at')
    def updated(self, obj):
        return jalali(obj.updated_at)

    @action(description='بستن تیکت‌های انتخاب‌شده')
    def close_tickets(self, request, queryset):
        count = queryset.update(status=Ticket.Status.CLOSED)
        self.message_user(request, f'{count} تیکت بسته شد.', messages.SUCCESS)


# -------------------- NOTIFICATIONS --------------------
@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = ('title', 'audience', 'kind', 'reads', 'sent')
    list_filter = ('kind', ('user', admin.EmptyFieldListFilter))
    search_fields = ('title', 'text', 'user__first_name', 'user__last_name', 'user__username')
    autocomplete_fields = ('user',)
    fields = ('title', 'text', ('kind', 'link'), 'user')
    list_per_page = 30

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user').prefetch_related('read_by')

    @display(description='گیرنده')
    def audience(self, obj):
        return obj.user.get_full_name() or obj.user.contact if obj.user else 'همه کاربران'

    @display(description='خوانده‌شده')
    def reads(self, obj):
        return obj.read_by.count()

    @display(description='زمان', ordering='created_at')
    def sent(self, obj):
        return jalali(obj.created_at)


# -------------------- CERTIFICATES --------------------
@admin.register(Certificate)
class CertificateAdmin(ModelAdmin):
    list_display = ('code', 'full_name', 'course', 'grade', 'issued', 'is_revoked')
    list_filter = ('is_revoked', 'course')
    list_filter_submit = True
    search_fields = ('code', 'full_name', 'user__username', 'user__phone_number', 'course__title')
    autocomplete_fields = ('user', 'course')
    readonly_fields = ('code', 'issued_at')
    fields = ('code', ('user', 'course'), 'full_name', 'grade', ('issued_at', 'is_revoked'))
    actions = ('revoke', 'restore')

    @display(description='تاریخ صدور', ordering='issued_at')
    def issued(self, obj):
        return jalali(obj.issued_at, False)

    @action(description='ابطال گواهی‌ها')
    def revoke(self, request, queryset):
        self.message_user(request, f'{queryset.update(is_revoked=True)} گواهی باطل شد.', messages.WARNING)

    @action(description='لغو ابطال')
    def restore(self, request, queryset):
        self.message_user(request, f'{queryset.update(is_revoked=False)} گواهی دوباره معتبر شد.', messages.SUCCESS)


# -------------------- CONTACT / NEWSLETTER --------------------
@admin.register(ContactMessage)
class ContactMessageAdmin(ModelAdmin):
    list_display = ('name', 'contact', 'subject', 'received', 'is_handled')
    list_filter = ('is_handled',)
    list_editable = ('is_handled',)
    search_fields = ('name', 'phone', 'email', 'subject', 'message')
    readonly_fields = ('name', 'phone', 'email', 'subject', 'message', 'user', 'created_at')
    fields = (('name', 'user'), ('phone', 'email'), 'subject', 'message', ('created_at', 'is_handled'))
    actions = ('mark_handled',)

    def has_add_permission(self, request):
        return False

    @display(description='تماس')
    def contact(self, obj):
        return obj.phone or obj.email

    @display(description='زمان', ordering='created_at')
    def received(self, obj):
        return jalali(obj.created_at)

    @action(description='علامت «بررسی شده»')
    def mark_handled(self, request, queryset):
        self.message_user(request, f'{queryset.update(is_handled=True)} پیام بررسی شد.', messages.SUCCESS)


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(ModelAdmin):
    list_display = ('phone_number', 'joined', 'is_active')
    list_filter = ('is_active',)
    list_editable = ('is_active',)
    search_fields = ('phone_number',)
    actions = ('export_csv',)

    @display(description='تاریخ عضویت', ordering='created_at')
    def joined(self, obj):
        return jalali(obj.created_at, False)

    @action(description='خروجی CSV شماره‌ها')
    def export_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="newsletter.csv"'
        response.write('﻿')  # Excel opens UTF-8 correctly with a BOM
        writer = csv.writer(response)
        writer.writerow(['phone_number', 'joined', 'active'])
        for subscriber in queryset:
            writer.writerow([subscriber.phone_number, jalali(subscriber.created_at, False), subscriber.is_active])
        return response
