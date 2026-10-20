from django.urls import path

from . import views

urlpatterns = [
    # Student panel (JWT)
    path('me/favorites/', views.FavoriteListAPIView.as_view(), name='me-favorites'),
    path('me/favorites/<int:course_id>/', views.FavoriteDeleteAPIView.as_view(), name='me-favorite-delete'),
    path('me/progress/', views.ProgressListAPIView.as_view(), name='me-progress'),
    path('me/progress/<int:course_id>/', views.CourseProgressAPIView.as_view(), name='me-course-progress'),
    path('me/certificates/', views.CertificateListAPIView.as_view(), name='me-certificates'),
    path('me/tickets/', views.TicketListCreateAPIView.as_view(), name='me-tickets'),
    path('me/tickets/<int:ticket_id>/', views.TicketDetailAPIView.as_view(), name='me-ticket'),
    path('me/tickets/<int:ticket_id>/reply/', views.TicketReplyAPIView.as_view(), name='me-ticket-reply'),
    path('me/tickets/<int:ticket_id>/close/', views.TicketCloseAPIView.as_view(), name='me-ticket-close'),
    path('me/notifications/', views.NotificationListAPIView.as_view(), name='me-notifications'),
    path('me/notifications/read/', views.NotificationReadAPIView.as_view(), name='me-notifications-read'),
    path('me/teacher/', views.TeacherApplicationAPIView.as_view(), name='me-teacher'),
    path('me/teacher/stats/', views.TeacherStatsAPIView.as_view(), name='me-teacher-stats'),

    # Public
    path('certificates/<str:code>/', views.CertificateVerifyAPIView.as_view(), name='certificate-verify'),
    path('contact/', views.ContactAPIView.as_view(), name='contact'),
    path('newsletter/', views.NewsletterAPIView.as_view(), name='newsletter'),
]
