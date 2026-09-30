from django.urls import include, path

from desk.views import health

urlpatterns = [
    path("health", health),
    path("health/", health),
    path("api/", include("desk.urls")),
]
