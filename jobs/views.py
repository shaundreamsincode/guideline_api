from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from .models import Job
from .tasks import process_guideline
import time

class JobCreateView(APIView):
    @extend_schema(
        summary="Create a new guideline processing job",
        description="Creates a new job to process clinical guidelines using GPT. Returns an event_id for tracking.",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'title': {'type': 'string', 'description': 'Optional title for the guideline'},
                    'guideline_text': {'type': 'string', 'description': 'The clinical guideline text to process'}
                },
                'required': ['guideline_text']
            }
        },
        responses={
            202: {
                'description': 'Job created successfully',
                'type': 'object',
                'properties': {
                    'event_id': {'type': 'string', 'format': 'uuid', 'description': 'Unique identifier for the job'}
                }
            },
            400: {
                'description': 'Bad request - missing required fields',
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'description': 'Error message'}
                }
            }
        },
        examples=[
            OpenApiExample(
                'Valid Request',
                value={
                    'title': 'Diabetes Management Guidelines',
                    'guideline_text': 'Patients with diabetes should monitor blood glucose daily...'
                },
                request_only=True
            ),
            OpenApiExample(
                'Success Response',
                value={'event_id': '123e4567-e89b-12d3-a456-426614174000'},
                response_only=True
            )
        ]
    )
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
    @extend_schema(
        summary="Get job status and results",
        description="Retrieves the current status and results of a guideline processing job.",
        parameters=[
                            OpenApiParameter(
                    name='event_id',
                    location=OpenApiParameter.PATH,
                    description='Unique identifier for the job',
                    required=True,
                    type=str
                )
        ],
        responses={
            200: {
                'description': 'Job details retrieved successfully',
                'type': 'object',
                'properties': {
                    'event_id': {'type': 'string', 'format': 'uuid', 'description': 'Unique identifier for the job'},
                    'status': {'type': 'string', 'enum': ['queued', 'processing', 'done', 'failed'], 'description': 'Current job status'},
                    'summary': {'type': 'string', 'description': 'Generated summary (only when status is done)'},
                    'checklist': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Generated checklist (only when status is done)'}
                }
            },
            404: {
                'description': 'Job not found',
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'description': 'Error message'}
                }
            }
        },
        examples=[
            OpenApiExample(
                'Queued Job',
                value={
                    'event_id': '123e4567-e89b-12d3-a456-426614174000',
                    'status': 'queued'
                },
                response_only=True
            ),
            OpenApiExample(
                'Completed Job',
                value={
                    'event_id': '123e4567-e89b-12d3-a456-426614174000',
                    'status': 'done',
                    'summary': 'This guideline outlines diabetes management protocols...',
                    'checklist': ['Monitor blood glucose daily', 'Take medications as prescribed', 'Schedule regular checkups']
                },
                response_only=True
            )
        ]
    )
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
