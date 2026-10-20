from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import PhoneOTP, User
from .phone import normalize_phone

PASSWORD = 'Str0ng-Passw0rd!'


@override_settings(DEBUG=True, SMS_BACKEND='console', OTP_RETURN_CODE_IN_DEBUG=True, OTP_RESEND_SECONDS=0)
class PhoneAuthTests(APITestCase):
    phone = '09121234567'

    def setUp(self):
        cache.clear()  # request throttling counters

    def send(self, purpose, phone=None):
        return self.client.post(reverse('otp-send'), {'phone_number': phone or self.phone, 'purpose': purpose})

    def verify(self, purpose, code):
        return self.client.post(reverse('otp-verify'), {'phone_number': self.phone, 'purpose': purpose, 'code': code})

    def register(self):
        code = self.send('register').data['debug_code']
        token = self.verify('register', code).data['verification_token']
        return self.client.post(reverse('phone-register'), {
            'verification_token': token, 'first_name': 'سارا', 'last_name': 'احمدی',
            'password': PASSWORD, 'password2': PASSWORD,
        })

    def test_normalize_phone(self):
        for value in ('09121234567', '۰۹۱۲۱۲۳۴۵۶۷', '+98 912 123 4567', '00989121234567', '9121234567'):
            self.assertEqual(normalize_phone(value), '09121234567')
        for value in ('', '0212345678', '0912123', 'abc'):
            self.assertIsNone(normalize_phone(value))

    def test_check_register_login(self):
        response = self.client.post(reverse('phone-check'), {'phone_number': '+989121234567'})
        self.assertEqual(response.data, {'phone_number': self.phone, 'exists': False, 'has_password': False})

        response = self.register()
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIn('access', response.data)
        user = User.objects.get(phone_number=self.phone)
        self.assertEqual(user.username, self.phone)
        self.assertIsNone(user.email)

        response = self.client.post(reverse('phone-check'), {'phone_number': self.phone})
        self.assertTrue(response.data['exists'])
        self.assertTrue(response.data['has_password'])

        # Login with password (Persian digits accepted)
        response = self.client.post(reverse('phone-login'), {'phone_number': '۰۹۱۲۱۲۳۴۵۶۷', 'password': PASSWORD})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['phone_number'], self.phone)
        response = self.client.post(reverse('phone-login'), {'phone_number': self.phone, 'password': 'wrong'})
        self.assertEqual(response.status_code, 401)

        # Login with an SMS code
        code = self.send('login').data['debug_code']
        response = self.verify('login', code)
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)

        # The profile works with the new token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        self.assertEqual(self.client.get(reverse('user-profile')).data['phone_number'], self.phone)

    def test_register_twice_is_refused(self):
        self.assertEqual(self.register().status_code, 201)
        response = self.send('register')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['code'], 'exists')

    def test_wrong_code_and_attempt_limit(self):
        code = self.send('register').data['debug_code']
        wrong = '0000' if code != '0000' else '1111'
        for _ in range(5):
            self.assertEqual(self.verify('register', wrong).status_code, 400)
        # Even the right code is refused after too many attempts
        response = self.verify('register', code)
        self.assertEqual(response.data['code'], 'expired')

    def test_code_is_single_use(self):
        code = self.send('register').data['debug_code']
        self.assertEqual(self.verify('register', code).status_code, 200)
        self.assertEqual(self.verify('register', code).status_code, 400)
        self.assertFalse(PhoneOTP.objects.filter(is_used=False).exists())

    def test_login_code_needs_an_account(self):
        response = self.send('login')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['code'], 'not_found')

    def test_token_purpose_is_checked(self):
        self.register()
        code = self.send('reset').data['debug_code']
        token = self.verify('reset', code).data['verification_token']
        # A reset token cannot be used to create an account
        response = self.client.post(reverse('phone-register'), {
            'verification_token': token, 'first_name': 'a', 'last_name': 'b', 'password': PASSWORD, 'password2': PASSWORD,
        })
        self.assertEqual(response.status_code, 400)

        new_password = 'An0ther-Passw0rd!'
        response = self.client.post(reverse('password-reset'), {'verification_token': token, 'password': new_password, 'password2': new_password})
        self.assertEqual(response.status_code, 200, response.data)
        response = self.client.post(reverse('phone-login'), {'phone_number': self.phone, 'password': new_password})
        self.assertEqual(response.status_code, 200)

    @override_settings(OTP_RESEND_SECONDS=120)
    def test_resend_wait(self):
        self.assertEqual(self.send('register').status_code, 200)
        response = self.send('register')
        self.assertEqual(response.status_code, 429)
        self.assertIn('resend_in', response.data)

    def test_email_accounts_still_work(self):
        response = self.client.post(reverse('user-register'), {
            'first_name': 'Ali', 'last_name': 'Rezaei', 'email': 'ali@test.com', 'password': PASSWORD, 'password2': PASSWORD,
        })
        self.assertEqual(response.status_code, 201)
        # Several accounts without an email / phone are allowed
        self.register()
        self.assertEqual(User.objects.filter(phone_number__isnull=True).count(), 1)
        self.assertEqual(User.objects.filter(email__isnull=True).count(), 1)
