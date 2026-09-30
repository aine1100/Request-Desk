from django.urls import path

from desk.views import (
    AnalyticsView,
    AssignmentCreateView,
    AssignmentDeleteView,
    EpisodeImportView,
    EpisodeListView,
    LoginView,
    MeView,
    RequestDetailView,
    RequestListCreateView,
    RequestTransitionView,
    UserDetailView,
    UserListCreateView,
)

urlpatterns = [
    path("auth/login/", LoginView.as_view()),
    path("auth/me/", MeView.as_view()),
    path("users/", UserListCreateView.as_view()),
    path("users/<int:pk>/", UserDetailView.as_view()),
    path("episodes/", EpisodeListView.as_view()),
    path("episodes/import/", EpisodeImportView.as_view()),
    path("requests/", RequestListCreateView.as_view()),
    path("requests/<int:pk>/", RequestDetailView.as_view()),
    path("requests/<int:pk>/transition/", RequestTransitionView.as_view()),
    path("requests/<int:pk>/assignments/", AssignmentCreateView.as_view()),
    path("requests/<int:pk>/assignments/<str:episode_id>/", AssignmentDeleteView.as_view()),
    path("analytics/", AnalyticsView.as_view()),
]
