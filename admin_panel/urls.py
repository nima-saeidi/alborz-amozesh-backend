from django.urls import path
from .views import AdminRegisterAPIView, AdminLoginAPIView

urlpatterns = [
    path('api/admin/register/', AdminRegisterAPIView.as_view(), name='register-admin'),
    path('api/admin/login/', AdminLoginAPIView.as_view(), name='login-admin')
]