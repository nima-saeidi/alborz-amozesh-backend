from django.urls import reverse
from rest_framework.test import APITestCase

from users.models import Course, Invoice, Teacher
from users.tests import make_user, make_teacher, PASSWORD
from .models import AdminProfile, Comment


class AdminApiTests(APITestCase):
    def setUp(self):
        self.super_admin = make_user('boss@test.com')
        AdminProfile.objects.create(user=self.super_admin, access_level=5)
        self.content_admin = make_user('content@test.com')
        AdminProfile.objects.create(user=self.content_admin, access_level=4)
        self.gallery_admin = make_user('gallery@test.com')
        AdminProfile.objects.create(user=self.gallery_admin, access_level=1)

    def test_login(self):
        response = self.client.post(reverse('login-admin'), {'email': 'boss@test.com', 'password': PASSWORD})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['access_level'], 5)

        make_user('student@test.com')
        response = self.client.post(reverse('login-admin'), {'email': 'student@test.com', 'password': PASSWORD})
        self.assertEqual(response.status_code, 401)

    def test_permissions_by_level(self):
        self.client.force_authenticate(self.gallery_admin)
        self.assertEqual(self.client.get(reverse('admin-gallery-list')).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin-courses-list')).status_code, 403)
        self.assertEqual(self.client.get(reverse('admin-dashboard')).status_code, 403)

        self.client.force_authenticate(self.content_admin)
        self.assertEqual(self.client.get(reverse('admin-dashboard')).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin-users-list')).status_code, 403)

        self.client.force_authenticate(self.super_admin)
        response = self.client.get(reverse('admin-users-list'), {'search': 'content'})
        self.assertEqual(response.data['count'], 1)

    def test_register_admin(self):
        self.client.force_authenticate(self.content_admin)
        payload = {'first_name': 'N', 'last_name': 'M', 'email': 'new@test.com', 'password': PASSWORD, 'access_level': 4}
        self.assertEqual(self.client.post(reverse('register-admin'), payload).status_code, 403)

        self.client.force_authenticate(self.super_admin)
        response = self.client.post(reverse('register-admin'), payload)
        self.assertEqual(response.status_code, 201, response.data)

    def test_teacher_approval_invoices_and_comments(self):
        teacher = make_teacher(approved=False)
        student = make_user('student@test.com')
        self.client.force_authenticate(self.content_admin)

        response = self.client.get(reverse('admin-teachers-list'), {'approved': 'false'})
        self.assertEqual(response.data['count'], 1)
        self.client.post(reverse('admin-teachers-approve', args=[teacher.id]))
        self.assertTrue(Teacher.objects.get(id=teacher.id).is_approved)

        course = Course.objects.create(title='C', teacher=teacher, cost=200000, discount_price=150000)
        invoice = Invoice.objects.create(student=student, course=course)
        response = self.client.post(reverse('admin-invoices-mark-paid', args=[invoice.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['paid'])
        self.assertEqual(int(response.data['amount']), 150000)

        response = self.client.get(reverse('admin-dashboard'))
        self.assertEqual(response.data['invoices']['paid'], 1)
        self.assertEqual(int(response.data['invoices']['revenue']), 150000)

        comment = Comment.objects.create(course=course, author=student, text='ok', rating=4)
        self.client.post(reverse('admin-comment-approve', args=[comment.id]))
        self.assertEqual(Comment.objects.get(id=comment.id).status, 'approved')

    def test_django_admin_pages_render(self):
        self.super_admin.is_staff = True
        self.super_admin.is_superuser = True
        self.super_admin.save()
        teacher = make_teacher()
        Course.objects.create(title='C', teacher=teacher, cost=1000)
        self.client.force_login(self.super_admin)

        for name in ['admin:index', 'admin:users_user_changelist', 'admin:users_course_changelist', 'admin:users_invoice_changelist',
                     'admin:users_teacher_changelist', 'admin:users_coursesession_changelist', 'admin:admin_panel_comment_changelist',
                     'admin:admin_panel_gallery_changelist', 'admin:admin_panel_banner_changelist', 'admin:admin_panel_partner_changelist',
                     'admin:users_course_add', 'admin:users_user_add']:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200, name)
        self.assertContains(self.client.get(reverse('admin:index')), 'دوره‌های فعال')
