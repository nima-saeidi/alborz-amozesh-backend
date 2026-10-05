"""
Who can see the files of a course, and signed links to the session files.
"""
from django.conf import settings
from django.core import signing
from django.urls import reverse

SESSION_FILE_SALT = 'users.session-file'
SESSION_FILE_KINDS = ('video', 'pdf')


def is_content_admin(user):
    """Django staff or admin API level >= 4"""
    if not user or not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    profile = getattr(user, 'admin_profile', None)
    return profile is not None and profile.access_level >= 4


def can_access_course_files(user, course):
    if not user or not user.is_authenticated:
        return False
    if is_content_admin(user):
        return True
    if course.teacher.user_id == user.id:
        return True
    return course.invoices.filter(student=user, paid=True).exists()


def can_access_session_files(user, session, course_access=None):
    if session.is_free:
        return True
    if course_access is not None:
        return course_access
    return can_access_course_files(user, session.course)


def make_session_file_url(request, session, kind):
    """Absolute link valid for SESSION_FILE_LINK_MAX_AGE seconds"""
    token = signing.dumps({'s': session.id, 'k': kind}, salt=SESSION_FILE_SALT)
    path = reverse('session-file', kwargs={'session_id': session.id, 'kind': kind})
    url = f"{path}?token={token}"
    return request.build_absolute_uri(url) if request else url


def read_session_file_token(token, session_id, kind):
    data = signing.loads(token, salt=SESSION_FILE_SALT, max_age=settings.SESSION_FILE_LINK_MAX_AGE)
    if data.get('s') != session_id or data.get('k') != kind:
        raise signing.BadSignature('Token does not match the file')
    return data
