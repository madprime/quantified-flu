from django.urls import path

from .views import (
    ReportListView,
    ReportNoSymptomsView,
    ReportSymptomsView,
    PublicReportsLinkView,
    # Customize reports
    ReportSetupView,
)  # TODO: add ReportDiagnosisView


app_name = "reports"

urlpatterns = [
    # TODO: Implement reporting of diagnostic testing.
    # path("diagnosis", ReportDiagnosisView.as_view(), name="diagnosis"),
    path("no-symptoms", ReportNoSymptomsView.as_view(), name="no-symptoms"),
    path("symptoms", ReportSymptomsView.as_view(), name="symptoms"),
    path(
        "list/member/<member_id>.csv",
        ReportListView.as_view(as_csv=True),
        name="list_member_csv",
    ),
    path(
        "list/member/<member_id>.json",
        ReportListView.as_view(as_json=True),
        name="list_member_json",
    ),
    path("list/member/<member_id>", ReportListView.as_view(), name="list_member"),
    path("list.csv", ReportListView.as_view(as_csv=True), name="list_csv"),
    path("list.json", ReportListView.as_view(as_json=True), name="list_json"),
    path("list", ReportListView.as_view(), name="list"),
    path("public", PublicReportsLinkView.as_view(), name="public"),
    path(
        "public.json", PublicReportsLinkView.as_view(as_json=True), name="public_json"
    ),
    path("setup", ReportSetupView.as_view(), name="report-setup"),
]
