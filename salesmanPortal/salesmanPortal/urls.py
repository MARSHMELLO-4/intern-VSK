"""
URL configuration for salesmanPortal project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static # This line is good, no need for the duplicate

urlpatterns = [
    path('admin/', admin.site.urls),
    path('',include('salesmanPanel.urls')),
]

# This is the correct way to serve static and media files during development (DEBUG = True)
# It should ONLY be in the if settings.DEBUG block.
# Do NOT put static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) outside this block
# if you intend to use a production web server (like Nginx) for static files.
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Remove the problematic line: urlpatterns += static(settings.STATIC_URL, document_root = settings.STATIC_URL)