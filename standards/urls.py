from django.urls import path

from .views import StandardCategoryListAPIView, StandardDetailAPIView, StandardFileAPIView, StandardListAPIView

# Mounted under /api/
urlpatterns = [
    path('standards/', StandardListAPIView.as_view(), name='standards'),
    path('standards/categories/', StandardCategoryListAPIView.as_view(), name='standard-categories'),
    path('standards/<int:id>/', StandardDetailAPIView.as_view(), name='standard-detail'),
    path('standards/<int:id>/file/', StandardFileAPIView.as_view(), name='standard-file'),
]
