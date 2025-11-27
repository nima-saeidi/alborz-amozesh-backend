from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AdminRegisterAPIView, AdminLoginAPIView, AdminUserViewSet, AdminGalleryViewSet, AdminCourseViewSet, AdminCommentViewSet

router = DefaultRouter()
router.register(r'api/admin/gallery', AdminGalleryViewSet, basename='admin-gallery')
router.register(r'api/admin/courses', AdminCourseViewSet, basename='admin-courses')
router.register(r'api/admin/users', AdminUserViewSet, basename='admin-users')
router.register(r'api/admin/comment', AdminCommentViewSet, basename='admin-comment')


urlpatterns = [
    path('api/admin/register/', AdminRegisterAPIView.as_view(), name='register-admin'),
    path('api/admin/login/', AdminLoginAPIView.as_view(), name='login-admin'),
    path('', include(router.urls)),

]