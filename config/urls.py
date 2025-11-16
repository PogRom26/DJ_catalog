from django.contrib import admin
from django.urls import path, include

app_name = 'catalog'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('catalog/', include('catalog.urls', namespace='catalog'))
]
