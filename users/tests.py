import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from admin_panel.models import Comment
from .models import User, Teacher, Course, CourseSession, Invoice

MEDIA_ROOT = tempfile.mkdtemp()
PASSWORD = 'Str0ng-Passw0rd!'


def make_user(email, **extra):
    user = User(username=email, email=email, first_name=extra.pop('first_name', 'Ali'), last_name=extra.pop('last_name', 'Rezaei'), **extra)
    user.set_password(PASSWORD)
    user.save()
    return user


def make_teacher(email='teacher@test.com', approved=True):
    return Teacher.objects.create(user=make_user(email), is_approved=approved)


@override_settings(MEDIA_ROOT=MEDIA_ROOT, PROTECTED_MEDIA_USE_ACCEL=False)
class BaseTestCase(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

    def login(self, user):
        self.client.force_authenticate(user)


class AuthTests(BaseTestCase):
    def test_register_login_refresh_logout(self):
        response = self.client.post(reverse('user-register'), {
            'first_name': 'Sara', 'last_name': 'Ahmadi', 'email': 'Sara@Test.com',
            'password': PASSWORD, 'password2': PASSWORD,
        })
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(User.objects.get().email, 'sara@test.com')

        # Login is case insensitive on the email
        response = self.client.post(reverse('login'), {'email': 'SARA@test.com', 'password': PASSWORD})
        self.assertEqual(response.status_code, 200)
        refresh = response.data['refresh']

        response = self.client.post(reverse('token-refresh'), {'refresh': refresh})
        self.assertEqual(response.status_code, 200)
        new_refresh = response.data['refresh']

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        response = self.client.post(reverse('logout'), {'refresh': new_refresh})
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse('token-refresh'), {'refresh': new_refresh})
        self.assertEqual(response.status_code, 401)

    def test_register_duplicate_email_and_password_mismatch(self):
        make_user('dup@test.com')
        response = self.client.post(reverse('user-register'), {
            'first_name': 'A', 'last_name': 'B', 'email': 'DUP@test.com', 'password': PASSWORD, 'password2': PASSWORD,
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.data)

        response = self.client.post(reverse('user-register'), {
            'first_name': 'A', 'last_name': 'B', 'email': 'new@test.com', 'password': PASSWORD, 'password2': 'other',
        })
        self.assertEqual(response.status_code, 400)

    def test_wrong_password(self):
        make_user('a@test.com')
        response = self.client.post(reverse('login'), {'email': 'a@test.com', 'password': 'wrong'})
        self.assertEqual(response.status_code, 401)

    def test_teacher_register_needs_approval(self):
        response = self.client.post(reverse('teacher-register'), {
            'first_name': 'Reza', 'last_name': 'Karimi', 'email': 'reza@test.com',
            'password': PASSWORD, 'password2': PASSWORD, 'academic_field': 'Math',
        })
        self.assertEqual(response.status_code, 201, response.data)
        self.assertFalse(response.data['teacher_approved'])

        user = User.objects.get(email='reza@test.com')
        self.login(user)
        response = self.client.post(reverse('teacher-course-create'), {'title': 'X'})
        self.assertEqual(response.status_code, 403)

        user.teacher.is_approved = True
        user.teacher.save()
        response = self.client.post(reverse('teacher-course-create'), {'title': 'X', 'cost': 100000})
        self.assertEqual(response.status_code, 201, response.data)

    def test_update_credentials(self):
        user = make_user('me@test.com')
        make_user('taken@test.com')
        self.login(user)

        response = self.client.put(reverse('update-credentials'), {'current_password': 'bad', 'email': 'x@test.com'})
        self.assertEqual(response.status_code, 400)
        response = self.client.put(reverse('update-credentials'), {'current_password': PASSWORD, 'email': 'taken@test.com'})
        self.assertEqual(response.status_code, 400)
        response = self.client.put(reverse('update-credentials'), {'current_password': PASSWORD, 'email': 'new@test.com'})
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.email, 'new@test.com')

    def test_profile_update(self):
        teacher = make_teacher()
        self.login(teacher.user)
        response = self.client.patch(reverse('update-profile'), {'first_name': 'New', 'bio': 'Hello'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        teacher.refresh_from_db()
        self.assertEqual(teacher.user.first_name, 'New')
        self.assertEqual(teacher.bio, 'Hello')


class CourseTests(BaseTestCase):
    def setUp(self):
        self.teacher = make_teacher()
        self.course = Course.objects.create(title='Python', teacher=self.teacher, cost=500000, category='Programming', limit_students=1)
        self.session = CourseSession.objects.create(
            course=self.course, title='Intro', order=1,
            video=SimpleUploadedFile('intro.mp4', b'video-bytes', content_type='video/mp4'),
        )
        self.free_session = CourseSession.objects.create(
            course=self.course, title='Preview', order=0, is_free=True,
            pdf=SimpleUploadedFile('preview.pdf', b'pdf-bytes', content_type='application/pdf'),
        )
        self.student = make_user('student@test.com')

    def test_public_list_and_detail(self):
        Course.objects.create(title='Hidden', teacher=self.teacher, is_active=False)
        response = self.client.get(reverse('list-courses'), {'search': 'pyth'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['sessions_count'], 2)

        response = self.client.get(reverse('course-detail', args=[self.course.id]))
        self.assertEqual(response.status_code, 200)
        sessions = {s['title']: s for s in response.data['sessions']}
        # Anonymous: no link to the paid session, link to the free preview
        self.assertIsNone(sessions['Intro']['video_url'])
        self.assertTrue(sessions['Intro']['has_video'])
        self.assertIsNotNone(sessions['Preview']['pdf_url'])

        response = self.client.get(reverse('course-categories'))
        self.assertEqual(response.data, [{'name': 'Programming', 'count': 1}])

    def test_enroll_flow_and_file_access(self):
        self.login(self.student)
        self.assertEqual(self.client.post(reverse('enroll-course'), {'course_id': 9999}).status_code, 404)

        response = self.client.post(reverse('enroll-course'), {'course_id': self.course.id})
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data['paid'])
        self.assertEqual(int(response.data['amount']), 500000)
        self.assertEqual(self.client.post(reverse('enroll-course'), {'course_id': self.course.id}).status_code, 400)

        # Not paid yet: still no access
        response = self.client.get(reverse('course-sessions', args=[self.course.id]))
        intro = [s for s in response.data['results'] if s['title'] == 'Intro'][0]
        self.assertIsNone(intro['video_url'])

        Invoice.objects.filter(student=self.student).update(paid=True)
        response = self.client.get(reverse('course-sessions', args=[self.course.id]))
        intro = [s for s in response.data['results'] if s['title'] == 'Intro'][0]
        self.assertIsNotNone(intro['video_url'])

        # The signed link works without authentication, a tampered one does not
        self.client.force_authenticate(None)
        response = self.client.get(intro['video_url'])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b''.join(response.streaming_content), b'video-bytes')
        self.assertEqual(self.client.get(intro['video_url'] + 'x').status_code, 403)
        url = reverse('session-file', args=[self.free_session.id, 'video'])
        self.assertEqual(self.client.get(url + '?token=abc').status_code, 403)

        # Paid enrollment cannot be removed, course is full
        self.login(self.student)
        self.assertEqual(self.client.delete(reverse('remove-course'), {'course_id': self.course.id}).status_code, 400)
        self.assertEqual(self.client.get(reverse('student-courses')).data['count'], 1)
        other = make_user('other@test.com')
        self.login(other)
        response = self.client.post(reverse('enroll-course'), {'course_id': self.course.id})
        self.assertEqual(response.status_code, 400)

    def test_free_course_is_paid_immediately_and_unpaid_can_be_removed(self):
        free = Course.objects.create(title='Free', teacher=self.teacher, cost=0)
        self.login(self.student)
        response = self.client.post(reverse('enroll-course'), {'course_id': free.id})
        self.assertTrue(response.data['paid'])

        self.client.post(reverse('enroll-course'), {'course_id': self.course.id})
        response = self.client.delete(reverse('remove-course'), {'course_id': self.course.id})
        self.assertEqual(response.status_code, 200)

    def test_teacher_manages_own_courses_and_sessions(self):
        other_teacher = make_teacher('t2@test.com')
        self.login(self.teacher.user)

        response = self.client.get(reverse('teacher-courses'))
        self.assertEqual(len(response.data), 1)

        response = self.client.post(
            reverse('teacher-sessions', args=[self.course.id]),
            {'title': 'Lesson 2', 'order': 2, 'pdf': SimpleUploadedFile('l2.pdf', b'pdf', content_type='application/pdf')},
            format='multipart',
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(response.data['has_pdf'])
        session_id = response.data['id']

        response = self.client.patch(reverse('teacher-session-detail', args=[session_id]), {'title': 'Lesson two'}, format='json')
        self.assertEqual(response.status_code, 200)

        response = self.client.patch(reverse('teacher-course-update', args=[self.course.id]), {'discount_price': 900000}, format='json')
        self.assertEqual(response.status_code, 400)

        # Another teacher cannot touch it
        self.login(other_teacher.user)
        self.assertEqual(self.client.get(reverse('teacher-course-detail', args=[self.course.id])).status_code, 404)
        self.assertEqual(self.client.delete(reverse('teacher-session-detail', args=[session_id])).status_code, 404)

        # Course with paid students cannot be deleted
        Invoice.objects.create(student=self.student, course=self.course, paid=True)
        self.login(self.teacher.user)
        self.assertEqual(self.client.delete(reverse('teacher-course-delete', args=[self.course.id])).status_code, 400)
        response = self.client.get(reverse('teacher-course-students', args=[self.course.id]))
        self.assertEqual(response.data['total_students'], 1)

    def test_teachers_and_comments(self):
        make_teacher('pending@test.com', approved=False)
        response = self.client.get(reverse('teachers'))
        self.assertEqual(response.data['count'], 1)

        self.login(self.student)
        response = self.client.post(reverse('comments'), {'course': self.course.id, 'text': 'Great', 'rating': 5})
        self.assertEqual(response.status_code, 400)

        Invoice.objects.create(student=self.student, course=self.course, paid=True)
        response = self.client.post(reverse('comments'), {'course': self.course.id, 'text': 'Great', 'rating': 5, 'status': 'approved'})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['status'], 'pending')

        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(reverse('comments'), {'course': self.course.id}).data['count'], 0)
        Comment.objects.update(status='approved')
        self.assertEqual(self.client.get(reverse('comments'), {'course': self.course.id}).data['count'], 1)
