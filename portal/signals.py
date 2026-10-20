"""Automatic notifications: payment confirmed, ticket answered, certificate issued"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from users.models import Invoice
from .models import Certificate, Notification, Ticket, TicketMessage


@receiver(pre_save, sender=Invoice)
def remember_paid_state(sender, instance, **kwargs):
    instance._was_paid = bool(instance.pk) and Invoice.objects.filter(pk=instance.pk, paid=True).exists()


@receiver(post_save, sender=Invoice)
def notify_payment(sender, instance, created, **kwargs):
    if not instance.paid or getattr(instance, '_was_paid', False):
        return
    free = not instance.amount
    Notification.objects.create(
        user=instance.student,
        kind=Notification.Kind.PAYMENT if not free else Notification.Kind.COURSE,
        title=f'دسترسی به «{instance.course.title}» فعال شد',
        text='ثبت‌نام رایگان انجام شد.' if free else 'پرداخت شما تایید شد؛ همه جلسات دوره باز است.',
        link=f'/learn/{instance.course_id}',
    )


@receiver(post_save, sender=TicketMessage)
def update_ticket(sender, instance, created, **kwargs):
    if not created:
        return
    ticket = instance.ticket
    ticket.status = Ticket.Status.ANSWERED if instance.is_staff_reply else Ticket.Status.OPEN
    ticket.save(update_fields=['status', 'updated_at'])
    if instance.is_staff_reply:
        Notification.objects.create(
            user=ticket.user,
            kind=Notification.Kind.TICKET,
            title=f'پاسخ تیکت {ticket.id}',
            text=f'پشتیبانی به «{ticket.subject}» پاسخ داد.',
            link=f'/panel/tickets?ticket={ticket.id}',
        )


@receiver(post_save, sender=Certificate)
def notify_certificate(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            user=instance.user,
            kind=Notification.Kind.COURSE,
            title='گواهی‌نامه صادر شد',
            text=f'گواهی پایان دوره «{instance.course.title}» با کد {instance.code} صادر شد.',
            link='/panel/certificates',
        )
