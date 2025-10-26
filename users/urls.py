# ===========================================
# users/urls.py
# ===========================================
from django.urls import path
from .views import RegisterAPIView, LoginAPIView,UpdateProfileAPIView , TeacherRegisterAPIView

urlpatterns = [
    path('api/user/register/', RegisterAPIView.as_view(), name='api-user-register'),
    path('api/teacher/register', TeacherRegisterAPIView.as_view(), name='api-teacher-register'),
    path('api/user/login/', LoginAPIView.as_view(), name='api-login'),
    path('api/user/profile/update/', UpdateProfileAPIView.as_view(), name='api-profile-update'),

]
