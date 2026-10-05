from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    AdminRegisterAPIView,
    AdminLoginAPIView,
    AdminMeAPIView,
    AdminDashboardAPIView,
    AdminUserViewSet,
    AdminTeacherViewSet,
    AdminCourseViewSet,
    AdminSessionViewSet,
    AdminInvoiceViewSet,
    AdminGalleryViewSet,
    AdminCommentViewSet,
    AdminBannerViewSet,
    AdminPartnerViewSet,
)

router = DefaultRouter()
router.register(r'users', AdminUserViewSet, basename='admin-users')
router.register(r'teachers', AdminTeacherViewSet, basename='admin-teachers')
router.register(r'courses', AdminCourseViewSet, basename='admin-courses')
router.register(r'sessions', AdminSessionViewSet, basename='admin-sessions')
router.register(r'invoices', AdminInvoiceViewSet, basename='admin-invoices')
router.register(r'gallery', AdminGalleryViewSet, basename='admin-gallery')
router.register(r'comment', AdminCommentViewSet, basename='admin-comment')
router.register(r'banner', AdminBannerViewSet, basename='admin-banner')
router.register(r'partner', AdminPartnerViewSet, basename='admin-partner')

# Mounted under /api/admin/
urlpatterns = [
    path('register/', AdminRegisterAPIView.as_view(), name='register-admin'),
    path('login/', AdminLoginAPIView.as_view(), name='login-admin'),
    path('me/', AdminMeAPIView.as_view(), name='admin-me'),
    path('dashboard/', AdminDashboardAPIView.as_view(), name='admin-dashboard'),
    path('', include(router.urls)),
]
