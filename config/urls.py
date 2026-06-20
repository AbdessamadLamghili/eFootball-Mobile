from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('accounts/', include('accounts.urls')),
    path('rewards/', include('rewards.urls')),
    path('missions/', include('missions.urls')),
    path('notifications/', include('notifications.urls')),
    path('ligues/', include('leagues.urls')),
    path('api/', include('api.urls')),
    # API docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

admin.site.site_header = 'eFootball Rewards Admin'
admin.site.site_title = 'eFootball Rewards'
admin.site.index_title = 'Tableau de bord Administration'
