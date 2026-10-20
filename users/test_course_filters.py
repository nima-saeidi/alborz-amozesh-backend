from django.urls import reverse
from rest_framework.test import APITestCase

from admin_panel.models import Comment
from .models import Course, Invoice, Teacher, User


def make_user(username):
    return User.objects.create_user(username=username, email=f'{username}@test.com', password='x', first_name='Ali', last_name='Rezaei')


class CourseFilterTests(APITestCase):
    def setUp(self):
        teacher = Teacher.objects.create(user=make_user('teacher'), is_approved=True)
        self.python = Course.objects.create(title='Python', teacher=teacher, cost=1690000, discount_price=1290000, limit_students=1)
        self.free = Course.objects.create(title='Free webinar', teacher=teacher, kind=Course.Kind.WEBINAR, cost=0)
        self.excel = Course.objects.create(title='Excel', teacher=teacher, cost=690000)
        student = make_user('student')
        Invoice.objects.create(student=student, course=self.python, amount=1290000, paid=True)
        Comment.objects.create(course=self.python, author=student, text='great', rating=5, status='approved')
        Comment.objects.create(course=self.python, author=student, text='ok', rating=4, status='approved')
        Comment.objects.create(course=self.python, author=student, text='hidden', rating=1, status='pending')

    def titles(self, **params):
        return [c['title'] for c in self.client.get(reverse('list-courses'), params).data['results']]

    def test_filters(self):
        self.assertEqual(self.titles(kind='webinar'), ['Free webinar'])
        self.assertEqual(set(self.titles(kind='course')), {'Python', 'Excel'})
        # max_price uses the discounted price
        self.assertEqual(set(self.titles(max_price=1300000)), {'Python', 'Free webinar', 'Excel'})
        self.assertEqual(set(self.titles(max_price=700000)), {'Free webinar', 'Excel'})
        self.assertEqual(self.titles(free=1), ['Free webinar'])
        # Python is full (1 paid student for 1 place)
        self.assertNotIn('Python', self.titles(available=1))
        self.assertEqual(self.titles(ordering='price'), ['Free webinar', 'Excel', 'Python'])

    def test_rating_counts_only_approved_reviews(self):
        data = self.client.get(reverse('course-detail', args=[self.python.id])).data
        self.assertEqual(data['reviews_count'], 2)
        self.assertEqual(data['rating'], 4.5)
        self.assertEqual(data['kind'], 'course')
        self.assertTrue(data['is_full'])
        excel = self.client.get(reverse('course-detail', args=[self.excel.id])).data
        self.assertIsNone(excel['rating'])
        self.assertEqual(excel['reviews_count'], 0)
