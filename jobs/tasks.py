import uuid
import time
import openai
import os

from celery import shared_task
from .models import Job

# Initialize OpenAI client with new API
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@shared_task(bind=True, max_retries=5, default_retry_delay=2)
def process_guideline(self, event_id):
    try:
        event_uuid = uuid.UUID(event_id)
        job = Job.objects.get(event_id=event_uuid)
    except Job.DoesNotExist:
        # Exponential backoff: 2s, 4s, 8s, 16s, 32s
        retry_delay = 2 ** (self.request.retries + 1)
        if self.request.retries < self.max_retries:
            raise self.retry(
                exc=Job.DoesNotExist("Job not ready yet."),
                countdown=retry_delay
            )
        else:
            # If we've exhausted retries, mark the job as failed
            try:
                job = Job.objects.get(event_id=event_uuid)
            except Job.DoesNotExist:
                # Job truly doesn't exist, can't mark as failed
                raise
            job.status = "failed"
            job.save()
            raise

    # Check if job is already being processed or completed
    if job.status in ['processing', 'done', 'failed']:
        return f"Job {event_id} already processed with status: {job.status}"

    job.status = "processing"
    job.save()

    try:
        # Step 1: Summarize
        summary_response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a medical summarization assistant."},
                {"role": "user", "content": f"Summarize the following clinical guideline:\n\n{job.guideline_text}"}
            ]
        )
        summary = summary_response.choices[0].message.content.strip()

        # Step 2: Generate checklist
        checklist_response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a medical assistant who converts summaries into action checklists."},
                {"role": "user", "content": f"Create a clear checklist from this summary:\n\n{summary}"}
            ]
        )
        checklist_text = checklist_response.choices[0].message.content.strip()
        checklist = [line.lstrip("-•* ").strip() for line in checklist_text.split("\n") if line.strip()]

        job.summary = summary
        job.checklist = checklist
        job.status = "done"
        job.save()
        
        return f"Successfully processed job {event_id}"
        
    except Exception as e:
        job.status = "failed"
        job.save()
        raise
