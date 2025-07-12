import uuid
from typing import List, Optional

from django.db import models


class Job(models.Model):
    """
    Model representing a guideline processing job.

    Each job processes clinical guideline text through a two-step GPT chain:
    1. Summarize the guideline text
    2. Generate a checklist from the summary
    """

    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("processing", "Processing"),
        ("done", "Done"),
        ("failed", "Failed"),
    ]

    event_id: uuid.UUID = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False
    )
    title: str = models.CharField(max_length=255)
    guideline_text: str = models.TextField(blank=False, null=False)
    summary: Optional[str] = models.TextField(null=True, blank=True)
    checklist: Optional[List[str]] = models.JSONField(null=True, blank=True)
    status: str = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="queued"
    )
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Job {self.event_id} - {self.title}"
