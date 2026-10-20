from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import User

PASSWORD = 'Str0ng-Passw0rd!'


class UsernameAuthTests(APITestCase):
    def setUp(self):
        cache.clear()  # request throttling counters

    def register(self, **extra):
        data = {'username': 'Sara.Ahmadi', 'first_name': 'سارا', 'last_name': 'احمدی', 'password': PASSWORD, 'password2': PASSWORD, **extra}
        return self.client.post(reverse('username-register'), data)

    def test_register_and_login_without_phone(self):
        response = self.register()
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['username'], 'sara.ahmadi')
        self.assertIsNone(response.data['phone_number'])
        self.assertIn('access', response.data)
        user = User.objects.get(username='sara.ahmadi')
        self.assertIsNone(user.phone_number)
        self.assertIsNone(user.email)

        login = self.client.post(reverse('username-login'), {'username': 'SARA.ahmadi', 'password': PASSWORD})
        self.assertEqual(login.status_code, 200, login.data)
        self.assertEqual(login.data['user_id'], user.id)

        wrong = self.client.post(reverse('username-login'), {'username': 'sara.ahmadi', 'password': 'nope-nope-1'})
        self.assertEqual(wrong.status_code, 401)

        profile = self.client.get(reverse('user-profile'), HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        self.assertEqual(profile.data['username'], 'sara.ahmadi')

    def test_duplicate_and_invalid_usernames(self):
        self.assertEqual(self.register().status_code, 201)
        self.assertIn('username', self.register().data)
        for bad in ('ab', '09121234567', 'سارا', 'admin', '_sara', 'sara ahmadi'):
            self.assertIn('username', self.register(username=bad).data, bad)
        check = self.client.post(reverse('username-check'), {'username': 'sara.ahmadi'})
        self.assertFalse(check.data['available'])
        self.assertTrue(self.client.post(reverse('username-check'), {'username': 'reza_1'}).data['available'])

    def test_password_rules(self):
        self.assertIn('password2', self.register(password2='other-Passw0rd').data)
        self.assertIn('password', self.register(password='123', password2='123').data)

    def test_login_with_email_or_phone(self):
        user = User(username='09121234567', phone_number='09121234567', email='a@b.com', first_name='a', last_name='b')
        user.set_password(PASSWORD)
        user.save()
        for identifier in ('a@b.com', '۰۹۱۲۱۲۳۴۵۶۷'):
            response = self.client.post(reverse('username-login'), {'username': identifier, 'password': PASSWORD})
            self.assertEqual(response.status_code, 200, identifier)
