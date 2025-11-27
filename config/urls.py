from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from catalog import views

app_name = "catalog"

urlpatterns = [
    path("admin/", admin.site.urls),
    path('home/', views.home, name='home'),
    path("catalog/", include("catalog.urls", namespace="catalog")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
