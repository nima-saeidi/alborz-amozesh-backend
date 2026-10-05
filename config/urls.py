from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions


schema_view = get_schema_view(
    openapi.Info(
        title='Alborz Institute API',
        default_version='v1',
        description='API آموزشگاه البرز - احراز هویت با هدر Authorization: Bearer <access>',
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


def health(request):
    return JsonResponse({'status': 'ok'})


urlpatterns = [
    # Django admin site
    path('admin/', admin.site.urls),

    # API documentation
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    # API
    path('api/health/', health, name='health'),
    path('api/admin/', include('admin_panel.urls')),
    path('api/', include('users.urls')),
]

# Media files in development (nginx serves them in production)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
