from django.urls import path
from .views import JobCreateView, JobDetailView

urlpatterns = [
    path("", JobCreateView.as_view(), name="create-job"),  # POST /jobs
    path("<uuid:event_id>/", JobDetailView.as_view(), name="job-detail"),  # GET /jobs/<event_id>
]
