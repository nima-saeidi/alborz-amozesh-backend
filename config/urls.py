from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.conf import settings
from django.conf.urls.static import static

# --------------------
# Swagger / Redoc Documentation
# --------------------
schema_view = get_schema_view(
    openapi.Info(
        title="My Project API",
        default_version='v1',
        description="Documentation of My Project API",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # --------------------
    # Admin Panel
    # --------------------
    path('admin/', admin.site.urls),

    # --------------------
    # API Documentation
    # --------------------
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    # --------------------
    # Application URLs
    # --------------------
    path('', include('users.urls')),  # User-related API endpoints
    path('', include('admin_panel.urls')),  # Admin panel API endpoints
]

# --------------------
# Serve media files in development
# --------------------
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
