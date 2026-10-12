from django.urls import include, path  # type: ignore[import-not-found]


urlpatterns = [
    path("auth/", include("authentication.urls")),
    path("company/", include("company.urls")),
    path("inventory/", include("inventory.urls")),
    path("fleet/", include("fleet.urls")),
    path("assets/", include("assets.urls")),
    path("procurement/", include("procurement.urls")),
    path("finance/", include("finance.urls")),
    path("reports/", include("reports.urls")),
]