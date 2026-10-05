from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    RegisterAPIView,
    TeacherRegisterAPIView,
    LoginAPIView,
    LogoutAPIView,
    UserProfileAPIView,
    UpdateProfileInfoAPIView,
    UpdateCredentialsAPIView,
    ListCoursesAPIView,
    CourseDetailAPIView,
    CourseSessionListAPIView,
    CourseCategoriesAPIView,
    TeacherListAPIView,
    TeacherDetailAPIView,
    PublicBannerListAPIView,
    PublicPartnerListAPIView,
    PublicGalleryListAPIView,
    CommentListCreateAPIView,
    EnrollCourseAPIView,
    RemoveCourseAPIView,
    StudentInvoiceListAPIView,
    StudentCoursesAPIView,
    TeacherCoursesListAPIView,
    TeacherCourseCreateAPIView,
    TeacherCourseDetailAPIView,
    TeacherCourseUpdateAPIView,
    TeacherCourseDeleteAPIView,
    TeacherCourseStudentsAPIView,
    TeacherSessionListCreateAPIView,
    TeacherSessionDetailAPIView,
    SessionFileAPIView,
)

urlpatterns = [
    # -------------------- AUTH --------------------
    path('auth/register/', RegisterAPIView.as_view(), name='user-register'),
    path('auth/teacher-register/', TeacherRegisterAPIView.as_view(), name='teacher-register'),
    path('auth/login/', LoginAPIView.as_view(), name='login'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/logout/', LogoutAPIView.as_view(), name='logout'),

    # -------------------- PROFILE --------------------
    path('profile/', UserProfileAPIView.as_view(), name='user-profile'),
    path('profile/update/', UpdateProfileInfoAPIView.as_view(), name='update-profile'),
    path('profile/update/credentials/', UpdateCredentialsAPIView.as_view(), name='update-credentials'),

    # -------------------- COURSES (public) --------------------
    path('courses/', ListCoursesAPIView.as_view(), name='list-courses'),
    path('courses/categories/', CourseCategoriesAPIView.as_view(), name='course-categories'),
    path('courses/<int:id>/', CourseDetailAPIView.as_view(), name='course-detail'),
    path('courses/<int:course_id>/sessions/', CourseSessionListAPIView.as_view(), name='course-sessions'),

    # -------------------- TEACHERS / SITE CONTENT (public) --------------------
    path('teachers/', TeacherListAPIView.as_view(), name='teachers'),
    path('teachers/<int:id>/', TeacherDetailAPIView.as_view(), name='teacher-detail'),
    path('banners/', PublicBannerListAPIView.as_view(), name='public-banners'),
    path('partners/', PublicPartnerListAPIView.as_view(), name='public-partners'),
    path('gallery/', PublicGalleryListAPIView.as_view(), name='public-gallery'),
    path('comments/', CommentListCreateAPIView.as_view(), name='comments'),

    # -------------------- STUDENT --------------------
    path('student/enroll/', EnrollCourseAPIView.as_view(), name='enroll-course'),
    path('student/remove/', RemoveCourseAPIView.as_view(), name='remove-course'),
    path('student/invoices/', StudentInvoiceListAPIView.as_view(), name='student-invoices'),
    path('student/courses/', StudentCoursesAPIView.as_view(), name='student-courses'),

    # -------------------- TEACHER --------------------
    path('teacher/courses/', TeacherCoursesListAPIView.as_view(), name='teacher-courses'),
    path('teacher/courses/create/', TeacherCourseCreateAPIView.as_view(), name='teacher-course-create'),
    path('teacher/courses/<int:course_id>/', TeacherCourseDetailAPIView.as_view(), name='teacher-course-detail'),
    path('teacher/courses/<int:course_id>/update/', TeacherCourseUpdateAPIView.as_view(), name='teacher-course-update'),
    path('teacher/courses/<int:course_id>/delete/', TeacherCourseDeleteAPIView.as_view(), name='teacher-course-delete'),
    path('teacher/courses/<int:course_id>/students/', TeacherCourseStudentsAPIView.as_view(), name='teacher-course-students'),
    path('teacher/courses/<int:course_id>/sessions/', TeacherSessionListCreateAPIView.as_view(), name='teacher-sessions'),
    path('teacher/sessions/<int:session_id>/', TeacherSessionDetailAPIView.as_view(), name='teacher-session-detail'),

    # -------------------- FILES --------------------
    path('files/sessions/<int:session_id>/<str:kind>/', SessionFileAPIView.as_view(), name='session-file'),
]
