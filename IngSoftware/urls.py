from django.contrib import admin
from django.urls import path, re_path, include
from django.views.static import serve
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", include('webApp.urls')),  # Incluir todas las rutas de tu app
    re_path(r'^media/(?P<path>.*)$',serve, {'document_root':settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$',serve, {'document_root':settings.STATIC_ROOT}),
]
