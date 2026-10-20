from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from users.models import Course, CourseSession, Invoice, Teacher, User
from .models import Certificate, Notification, Ticket, TicketMessage

PASSWORD = 'Str0ng-Passw0rd!'


def make_user(username, **extra):
    user = User(username=username, first_name='سارا', last_name='احمدی', **extra)
    user.set_password(PASSWORD)
    user.save()
    return user


class PortalTests(APITestCase):
    def setUp(self):
        cache.clear()
        teacher_user = make_user('teacher1')
        self.teacher = Teacher.objects.create(user=teacher_user, is_approved=True)
        self.course = Course.objects.create(title='پایتون', teacher=self.teacher, cost=100000)
        self.s1 = CourseSession.objects.create(course=self.course, title='جلسه ۱', order=1)
        self.s2 = CourseSession.objects.create(course=self.course, title='جلسه ۲', order=2)
        self.user = make_user('student1')
        self.client.force_authenticate(self.user)

    def pay(self):
        invoice = Invoice.objects.create(student=self.user, course=self.course, amount=100000)
        invoice.paid = True
        invoice.paid_at = timezone.now()
        invoice.save()
        return invoice

    def test_favorites(self):
        response = self.client.post(reverse('me-favorites'), {'courses': [self.course.id, 9999]}, format='json')
        self.assertEqual(response.data, [self.course.id])
        self.assertEqual(self.client.get(reverse('me-favorites')).data, [self.course.id])
        self.assertEqual(self.client.delete(reverse('me-favorite-delete', args=[self.course.id])).data, [])

    def test_progress_needs_access(self):
        url = reverse('me-course-progress', args=[self.course.id])
        self.assertEqual(self.client.post(url, {'session': self.s1.id}).status_code, 403)
        self.pay()
        data = self.client.post(url, {'session': self.s1.id}).data
        self.assertEqual((data['done'], data['total'], data['percent']), (1, 2, 50))
        data = self.client.post(url, {'session': self.s1.id, 'done': False}, format='json').data
        self.assertEqual(data['done'], 0)
        self.assertEqual(self.client.get(reverse('me-progress')).data, {})

    def test_certificate_after_all_sessions(self):
        self.pay()
        url = reverse('me-certificates')
        self.assertEqual(self.client.post(url, {'course': self.course.id}).status_code, 400)
        for session in (self.s1, self.s2):
            self.client.post(reverse('me-course-progress', args=[self.course.id]), {'session': session.id})
        response = self.client.post(url, {'course': self.course.id})
        self.assertEqual(response.status_code, 201)
        code = response.data['code']
        self.assertTrue(code.startswith('ALB-'))
        # Asking again returns the same certificate
        self.assertEqual(self.client.post(url, {'course': self.course.id}).data['code'], code)
        listing = self.client.get(url).data
        self.assertEqual(listing['courses'][0]['certificate'], code)

        self.client.force_authenticate(None)
        verify = self.client.get(reverse('certificate-verify', args=[code.lower()]))
        self.assertTrue(verify.data['valid'])
        self.assertEqual(verify.data['course_title'], 'پایتون')
        Certificate.objects.update(is_revoked=True)
        self.assertEqual(self.client.get(reverse('certificate-verify', args=[code])).status_code, 404)

    def test_certificate_needs_enrollment(self):
        self.assertEqual(self.client.post(reverse('me-certificates'), {'course': self.course.id}).status_code, 403)

    def test_tickets_and_notifications(self):
        response = self.client.post(reverse('me-tickets'), {'subject': 'مشکل ویدیو', 'department': 'technical', 'text': 'ویدیو جلسه دوم پخش نمی‌شود.'})
        self.assertEqual(response.status_code, 201, response.data)
        ticket_id = response.data['id']
        self.assertEqual(response.data['status'], 'open')
        self.assertEqual(len(response.data['messages']), 1)

        # Staff reply (from the admin panel) answers the ticket and notifies the user
        TicketMessage.objects.create(ticket_id=ticket_id, text='بررسی شد، دوباره امتحان کنید.', is_staff_reply=True)
        self.assertEqual(Ticket.objects.get(id=ticket_id).status, 'answered')
        notifications = self.client.get(reverse('me-notifications')).data
        self.assertEqual(notifications['unread'], 1)
        self.assertEqual(notifications['results'][0]['kind'], 'ticket')

        self.client.post(reverse('me-ticket-reply', args=[ticket_id]), {'text': 'درست شد، ممنون'})
        self.assertEqual(Ticket.objects.get(id=ticket_id).status, 'open')
        self.client.post(reverse('me-ticket-close', args=[ticket_id]))
        self.assertEqual(self.client.post(reverse('me-ticket-reply', args=[ticket_id]), {'text': 'سلام'}).status_code, 400)

        # Other users cannot see it
        self.client.force_authenticate(make_user('other'))
        self.assertEqual(self.client.get(reverse('me-ticket', args=[ticket_id])).status_code, 404)

    def test_announcements_and_read_state(self):
        Notification.objects.create(title='اطلاعیه همگانی')
        self.pay()  # payment notification
        data = self.client.get(reverse('me-notifications')).data
        self.assertEqual(data['unread'], 2)
        self.assertEqual(self.client.post(reverse('me-notifications-read'), {}, format='json').data['unread'], 0)

    def test_teacher_application(self):
        self.assertEqual(self.client.get(reverse('me-teacher')).data['status'], 'none')
        response = self.client.post(reverse('me-teacher'), {'academic_field': 'برق', 'bio': 'ده سال تجربه'})
        self.assertEqual(response.data['status'], 'pending')
        self.assertEqual(self.client.post(reverse('me-teacher'), {}).status_code, 400)
        self.assertEqual(self.client.get(reverse('me-teacher-stats')).status_code, 403)

    def test_contact_and_newsletter(self):
        self.client.force_authenticate(None)
        self.assertIn('phone', self.client.post(reverse('contact'), {'name': 'علی', 'message': 'سلام، درباره دوره برق سوال دارم.'}).data)
        self.assertEqual(self.client.post(reverse('contact'), {'name': 'علی', 'phone': '09121234567', 'message': 'سلام، درباره دوره برق سوال دارم.'}).status_code, 201)
        self.assertEqual(self.client.post(reverse('newsletter'), {'phone_number': '۰۹۱۲۱۲۳۴۵۶۷'}).status_code, 201)
        self.assertEqual(self.client.post(reverse('newsletter'), {'phone_number': '09121234567'}).status_code, 200)
        self.assertEqual(self.client.post(reverse('newsletter'), {'phone_number': '123'}).status_code, 400)
