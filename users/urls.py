from django.urls import path
from .views import (
    RegisterAPIView,
    TeacherRegisterAPIView,
    LoginAPIView,
    UpdateProfileInfoAPIView,     # آپدیت اطلاعات تکمیلی
    UpdateCredentialsAPIView,     # آپدیت ایمیل و پسورد
    UserProfileAPIView,
    ListCoursesAPIView,
    CourseDetailAPIView,
    CourseSessionListAPIView,
    EnrollCourseAPIView,
    RemoveCourseAPIView,
    StudentInvoiceListAPIView,
    TeacherCoursesListAPIView,
    TeacherCourseDetailAPIView,
    TeacherCourseStudentsAPIView,
    TeacherCourseCreateAPIView,
    TeacherCourseUpdateAPIView,
    TeacherCourseDeleteAPIView,
    PublicBannerListAPIView
)

urlpatterns = [
    # -------------------- AUTH --------------------
    path('auth/register/', RegisterAPIView.as_view(), name='user-register'),
    path('auth/teacher-register/', TeacherRegisterAPIView.as_view(), name='teacher-register'),
    path('auth/login/', LoginAPIView.as_view(), name='login'),

    # -------------------- PROFILE --------------------
    path('profile/', UserProfileAPIView.as_view(), name='user-profile'),
    path('profile/update/', UpdateProfileInfoAPIView.as_view(), name='update-profile'),  # آپدیت سایر اطلاعات
    path('profile/update/credentials/', UpdateCredentialsAPIView.as_view(), name='update-credentials'),  # آپدیت ایمیل و پسورد

    # -------------------- COURSES --------------------
    path('courses/', ListCoursesAPIView.as_view(), name='list-courses'),
    path('courses/<int:id>/', CourseDetailAPIView.as_view(), name='course-detail'),

    # -------------------- COURSE SESSIONS --------------------
    path('courses/<int:course_id>/sessions/', CourseSessionListAPIView.as_view(), name='course-sessions'),

    # -------------------- STUDENT COURSE MANAGEMENT --------------------
    path('student/enroll/', EnrollCourseAPIView.as_view(), name='enroll-course'),
    path('student/remove/', RemoveCourseAPIView.as_view(), name='remove-course'),
    path('student/invoices/', StudentInvoiceListAPIView.as_view(), name='student-invoices'),

    # -------------------- TEACHER COURSE MANAGEMENT --------------------
    path('teacher/courses/', TeacherCoursesListAPIView.as_view(), name='teacher-courses'),
    path('teacher/courses/create/', TeacherCourseCreateAPIView.as_view(), name='teacher-course-create'),
    path('teacher/courses/<int:course_id>/', TeacherCourseDetailAPIView.as_view(), name='teacher-course-detail'),
    path('teacher/courses/<int:course_id>/update/', TeacherCourseUpdateAPIView.as_view(), name='teacher-course-update'),
    path('teacher/courses/<int:course_id>/delete/', TeacherCourseDeleteAPIView.as_view(), name='teacher-course-delete'),
    path('teacher/courses/<int:course_id>/students/', TeacherCourseStudentsAPIView.as_view(), name='teacher-course-students'),
    # -------------------- TEACHER COURSE MANAGEMENT --------------------

    path('banners/', PublicBannerListAPIView.as_view(), name='public-banners'),

]
