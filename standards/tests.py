import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from admin_panel.models import AdminProfile
from users.models import User
from .models import StandardCategory, TechnicalStandard

MEDIA_ROOT = tempfile.mkdtemp()


def pdf(name='standard.pdf'):
    return SimpleUploadedFile(name, b'%PDF-1.4 test', content_type='application/pdf')


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class StandardTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.it = StandardCategory.objects.create(title='فناوری اطلاعات')
        self.electric = StandardCategory.objects.create(title='برق')
        self.python = TechnicalStandard.objects.create(title='برنامه‌نویس پایتون', code='251340530120001', category=self.it, hours=240, pdf=pdf())
        TechnicalStandard.objects.create(title='تکنسین شبکه', code='351320530240001', category=self.it, pdf=pdf())
        TechnicalStandard.objects.create(title='پیش‌نویس', category=self.electric, pdf=pdf(), is_published=False)

    def test_public_list_search_and_category(self):
        response = self.client.get(reverse('standards'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertTrue(response.data['results'][0]['pdf'].endswith('.pdf'))

        self.assertEqual(self.client.get(reverse('standards'), {'search': 'پایتون'}).data['count'], 1)
        self.assertEqual(self.client.get(reverse('standards'), {'search': '351320'}).data['count'], 1)
        self.assertEqual(self.client.get(reverse('standards'), {'category': self.electric.id}).data['count'], 0)

        # Only categories with published standards
        categories = self.client.get(reverse('standard-categories')).data
        self.assertEqual([(c['title'], c['standards_count']) for c in categories], [('فناوری اطلاعات', 2)])

    def test_download_counts_and_redirects(self):
        response = self.client.get(reverse('standard-file', args=[self.python.id]))
        self.assertEqual(response.status_code, 302)
        self.python.refresh_from_db()
        self.assertEqual(self.python.downloads, 1)
        hidden = TechnicalStandard.objects.get(is_published=False)
        self.assertEqual(self.client.get(reverse('standard-file', args=[hidden.id])).status_code, 404)

    def test_admin_api_upload(self):
        url = '/api/admin/standards/'
        data = {'title': 'حسابدار', 'code': '1', 'category': self.it.id, 'pdf': pdf('acc.pdf')}
        self.assertEqual(self.client.post(url, data, format='multipart').status_code, 401)

        admin = User.objects.create_user(username='admin@test.com', email='admin@test.com', password='x')
        AdminProfile.objects.create(user=admin, access_level=4)
        self.client.force_authenticate(admin)
        response = self.client.post(url, {**data, 'pdf': pdf('acc.pdf')}, format='multipart')
        self.assertEqual(response.status_code, 201, response.data)

        # Only PDF files are accepted
        bad = SimpleUploadedFile('notes.txt', b'hello', content_type='text/plain')
        response = self.client.post(url, {**data, 'pdf': bad}, format='multipart')
        self.assertEqual(response.status_code, 400)
