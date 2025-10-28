from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls', namespace='core')),
    path('', include('institution.urls', namespace='institution')),
    path('gov/', include('government.urls', namespace='government')),
    path('accounts/', include('django.contrib.auth.urls')),
]