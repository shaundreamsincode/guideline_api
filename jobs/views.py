from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from .models import Job
from .tasks import process_guideline
import time

class JobCreateView(APIView):
    def post(self, request):
        title = request.data.get("title")
        guideline_text = request.data.get("guideline_text")

        if not guideline_text:
            return Response({"error": "Missing guideline_text"}, status=400)

        with transaction.atomic():
            job = Job.objects.create(
                title=title or "Untitled Guideline",
                guideline_text=guideline_text,
                status="queued",
            )

            # Only launch the task once the DB commit is done
            # Add a small delay to ensure transaction is fully committed
            def launch_task():
                time.sleep(0.1)  # 100ms delay
                process_guideline.delay(str(job.event_id))
            
            transaction.on_commit(launch_task)

        return Response({"event_id": job.event_id}, status=202)


class JobDetailView(APIView):
    def get(self, request, event_id):
        try:
            job = Job.objects.get(event_id=event_id)
        except Job.DoesNotExist:
            return Response({"error": "Job not found"}, status=404)

        return Response({
            "event_id": str(job.event_id),
            "status": job.status,
            "summary": job.summary,
            "checklist": job.checklist,
        })
