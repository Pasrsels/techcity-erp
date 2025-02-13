from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path
from django.views import defaults as default_views
from apps.company.views import verify_email

urlpatterns = [
    path('pos/', include('apps.pos.urls', namespace='pos')),
    path("admin/", admin.site.urls),
    path('users/', include('apps.users.urls', namespace='users')),
    path('', include('apps.company.urls', namespace='company')),
    path('finance/', include('apps.finance.urls', namespace='finance')),
    path('settings/', include('apps.settings.urls', namespace='settings')),
    # path('analytics/', include('Analytics.urls', namespace='analytics')),
    path('inventory/', include('apps.inventory.urls', namespace='inventory')),
    path('dashboard/', include('apps.Dashboard.urls', namespace='dashboard')),
    path('booking', include('apps.booking.urls', namespace='booking')),
    path('verify/<uidb64>/<token>/', verify_email, name='verify_email'),
    # path('__reload__/', include('django_browser_reload.urls')),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns

    # if settings.DEBUG:
    #     import debug_toolbar
    #     urlpatterns = [
    #         path('__debug__/', include(debug_toolbar.urls)),
    #     ] + urlpatterns