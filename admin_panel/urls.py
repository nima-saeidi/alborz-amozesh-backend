from django.urls import path
from .views import AdminRegisterAPIView, AdminLoginAPIView, GalleryCreateAPIView, CreateCourseAPIView, UserListAPIView, AdminUserUpdateAPIView

urlpatterns = [
    path('api/admin/register/', AdminRegisterAPIView.as_view(), name='register-admin'),
    path('api/admin/login/', AdminLoginAPIView.as_view(), name='login-admin'),
    path('api/admin/gallery/add/', GalleryCreateAPIView.as_view(), name='add-gallery'),
    path('api/admin/courses/create/', CreateCourseAPIView.as_view(), name='create-course'),
    path('api/admin/users/', UserListAPIView.as_view(), name='admin-user-list'),
    path('api/admin/users/<int:pk>/update/', AdminUserUpdateAPIView.as_view(), name='admin-user-update'),

]