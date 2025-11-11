from django.urls import path
from .views import (
    RegisterAPIView,
    TeacherRegisterAPIView,
    LoginAPIView,
    UpdateProfileAPIView,
    SelectCourseAPIView,
    RemoveCourseAPIView,
    ListCoursesAPIView,
    ListTeachersAPIView,
    UserProfileAPIView,
)

urlpatterns = [
    # --------------------
    # User Registration
    # --------------------
    path('api/users/register/student/', RegisterAPIView.as_view(), name='register-student'),  # Register a student
    path('api/users/register/teacher/', TeacherRegisterAPIView.as_view(), name='register-teacher'),  # Register a teacher

    # --------------------
    # User Login
    # --------------------
    path('api/users/login/', LoginAPIView.as_view(), name='login'),  # Login user (student or teacher)

    # --------------------
    # Profile Management
    # --------------------
    path('api/users/profile/update/', UpdateProfileAPIView.as_view(), name='update-profile'),  # Update user or teacher profile

    # --------------------
    # Course Selection (for testing purposes)
    # --------------------
    path('api/users/courses/select/', SelectCourseAPIView.as_view(), name='select-course'),  # Select a course
    path('api/users/courses/remove/', RemoveCourseAPIView.as_view(), name='remove-course'),  # Remove a course

    # --------------------
    # List all courses and teachers
    # --------------------
    path('api/courses/', ListCoursesAPIView.as_view(), name='list-courses'),  # List all available courses
    path('api/teachers/', ListTeachersAPIView.as_view(), name='list-teachers'),  # List all teachers

    # --------------------
    # User Profile with Selected Courses
    # --------------------
    path('api/users/profile/', UserProfileAPIView.as_view(), name='user-profile'),  # Retrieve user profile with selected courses
]
