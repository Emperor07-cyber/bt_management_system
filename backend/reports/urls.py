from django.urls import path

from .views import (
    DashboardView,
    GlobalSearchView,
    NotificationsView,
)

urlpatterns = [
    path(
        "dashboard/",
        DashboardView.as_view(),
        name="dashboard",
    ),

    path(
        "search/",
        GlobalSearchView.as_view(),
        name="global-search",
    ),

    path(
        "notifications/",
        NotificationsView.as_view(),
        name="notifications",
    ),
]