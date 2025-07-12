import logging
import os
import time
import uuid
from typing import List, Optional

import openai
from celery import shared_task

from .models import Job

# Set up logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client with new API
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable is required")

client = openai.OpenAI(api_key=api_key)


@shared_task(bind=True, max_retries=5, default_retry_delay=2)
def process_guideline(self, event_id: str) -> str:
    """
    Process a guideline through a two-step GPT chain.

    This Celery task performs the following steps:
    1. Summarize the guideline text using GPT-4
    2. Generate a checklist from the summary using GPT-4
    3. Save results to the database

    Args:
        event_id: The unique identifier of the job to process

    Returns:
        A success message string

    Raises:
        Job.DoesNotExist: If the job doesn't exist after retries
        Exception: For any other processing errors
    """
    try:
        event_uuid = uuid.UUID(event_id)
        job = Job.objects.get(event_id=event_uuid)
    except Job.DoesNotExist:
        # Exponential backoff: 2s, 4s, 8s, 16s, 32s
        retry_delay = 2 ** (self.request.retries + 1)
        if self.request.retries < self.max_retries:
            logger.warning(
                f"Job {event_id} not found, retrying in {retry_delay}s (attempt {self.request.retries + 1}/{self.max_retries})"
            )
            raise self.retry(
                exc=Job.DoesNotExist("Job not ready yet."), countdown=retry_delay
            )
        else:
            # If we've exhausted retries, mark the job as failed
            try:
                job = Job.objects.get(event_id=event_uuid)
            except Job.DoesNotExist:
                # Job truly doesn't exist, can't mark as failed
                logger.error(f"Job {event_id} not found after max retries")
                raise
            job.status = "failed"
            job.save()
            logger.error(f"Job {event_id} marked as failed after max retries")
            raise

    # Check if job is already being processed or completed
    if job.status in ["processing", "done", "failed"]:
        logger.info(f"Job {event_id} already processed with status: {job.status}")
        return f"Job {event_id} already processed with status: {job.status}"

    job.status = "processing"
    job.save()
    logger.info(f"Started processing job {event_id}")

    try:
        # Step 1: Summarize
        logger.info(f"Generating summary for job {event_id}")
        summary_response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a medical summarization assistant.",
                },
                {
                    "role": "user",
                    "content": f"Summarize the following clinical guideline:\n\n{job.guideline_text}",
                },
            ],
        )
        summary = summary_response.choices[0].message.content.strip()

        # Step 2: Generate checklist
        logger.info(f"Generating checklist for job {event_id}")
        checklist_response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a medical assistant who converts summaries into action checklists.",
                },
                {
                    "role": "user",
                    "content": f"Create a clear checklist from this summary:\n\n{summary}",
                },
            ],
        )
        checklist_text = checklist_response.choices[0].message.content.strip()
        checklist: List[str] = [
            line.lstrip("-•* ").strip()
            for line in checklist_text.split("\n")
            if line.strip()
        ]

        job.summary = summary
        job.checklist = checklist
        job.status = "done"
        job.save()

        logger.info(f"Successfully completed job {event_id}")
        return f"Successfully processed job {event_id}"

    except Exception as e:
        logger.error(f"Error processing job {event_id}: {str(e)}")
        job.status = "failed"
        job.save()
        raise
