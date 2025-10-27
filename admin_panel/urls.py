from django.urls import path
from .views import AdminRegisterAPIView, AdminLoginAPIView, GalleryCreateAPIView

urlpatterns = [
    path('api/admin/register/', AdminRegisterAPIView.as_view(), name='register-admin'),
    path('api/admin/login/', AdminLoginAPIView.as_view(), name='login-admin'),
    path('api/admin/gallery/add/', GalleryCreateAPIView.as_view(), name='add-gallery'),
]