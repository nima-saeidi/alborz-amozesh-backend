# ===========================================
# users/urls.py
# ===========================================
from django.urls import path
from .views import RegisterAPIView, LoginAPIView,UpdateProfileAPIView

urlpatterns = [
    path('api/user/register/', RegisterAPIView.as_view(), name='api-register'),
    path('api/user/login/', LoginAPIView.as_view(), name='api-login'),
    path('api/user/profile/update/', UpdateProfileAPIView.as_view(), name='api-profile-update'),

]
