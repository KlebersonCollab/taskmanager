from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Rota do TaskManager Dashboard
    path("tasks/", include("taskmanager.contrib.django.urls")),
]
