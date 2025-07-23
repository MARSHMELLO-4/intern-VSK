# salesmanPortal/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # 1. ALWAYS put the Django Admin URL FIRST and specifically.
    path('admin/', admin.site.urls),

    # 2. Then, include your application's URLs.
    #    The empty string '' means that salesmanPanel.urls patterns
    #    will be directly accessible at the root of your domain.
    path('', include('salesmanPanel.urls')),
]

# 3. ONLY put the static and media file serving patterns LAST,
#    and strictly inside the DEBUG block. These are catch-all patterns
#    for development and should not interfere with your defined URLs.
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Ensure no other static() or re_path(r'^(?P<path>.*)$', ...) patterns exist here
    # that could be placed before the admin/ or your app URLs.