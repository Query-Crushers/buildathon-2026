"""URL configuration for the project."""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.static import serve
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    return Response({
        'status': 'ok',
        'message': 'Hello from Django!',
        'oauth_enabled': bool(settings.CAYU_OAUTH_CLIENT_ID and settings.CAYU_OAUTH_AUTHORIZE_URL),
    })


admin.site.site_header = "Cayu Admin Panel"
admin.site.site_title = "Cayu Admin Panel"
admin.site.index_title = "Cayu Admin Panel"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health, name='health'),
    path('accounts/', include('apps.accounts.urls')),
    path('api/', include('apps.switchguard.urls')),
]

# Serve media files when using local storage (dev instances).
# In production (ECS), USE_S3=true so media is served from S3 directly.
if not settings.USE_S3:
    urlpatterns += [
        path('media/<path:path>', serve, {'document_root': settings.MEDIA_ROOT}),
    ]

# API documentation - only available in DEBUG mode
if settings.DEBUG:
    from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

    urlpatterns += [
        path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
        path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    ]
