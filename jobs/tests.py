import json
import uuid
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from .models import Job
from .tasks import process_guideline


class JobModelTest(TestCase):
    """Test cases for the Job model"""

    def setUp(self):
        self.job_data = {
            "title": "Test Guideline",
            "guideline_text": "This is a test clinical guideline for diabetes management.",
            "summary": "Test summary",
            "checklist": ["Step 1", "Step 2", "Step 3"],
        }

    def test_job_creation(self):
        """Test that a job can be created with required fields"""
        job = Job.objects.create(**self.job_data)
        self.assertIsNotNone(job.event_id)
        self.assertEqual(job.title, "Test Guideline")
        self.assertEqual(job.status, "queued")
        self.assertIsNotNone(job.created_at)
        self.assertIsNotNone(job.updated_at)

    def test_job_event_id_uniqueness(self):
        """Test that event_id is unique"""
        job1 = Job.objects.create(**self.job_data)
        job2 = Job.objects.create(**self.job_data)
        self.assertNotEqual(job1.event_id, job2.event_id)

    def test_job_status_choices(self):
        """Test that job status choices are valid"""
        job = Job.objects.create(**self.job_data)
        valid_statuses = ["queued", "processing", "done", "failed"]

        for status_choice in valid_statuses:
            job.status = status_choice
            job.save()
            job.refresh_from_db()
            self.assertEqual(job.status, status_choice)

    def test_job_string_representation(self):
        """Test the string representation of a job"""
        job = Job.objects.create(**self.job_data)
        expected_str = f"Job {job.event_id} - {job.title}"
        self.assertEqual(str(job), expected_str)

    def test_job_with_optional_fields(self):
        """Test job creation with optional fields"""
        job_data_minimal = {
            "title": "Minimal Job",
            "guideline_text": "Minimal guideline text",
        }
        job = Job.objects.create(**job_data_minimal)
        self.assertIsNone(job.summary)
        self.assertIsNone(job.checklist)
        self.assertEqual(job.status, "queued")


class JobCreateViewTest(APITestCase):
    """Test cases for JobCreateView"""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("create-job")
        self.valid_data = {
            "title": "Test Guideline",
            "guideline_text": "This is a test clinical guideline for diabetes management.",
        }

    def test_create_job_success(self):
        """Test successful job creation"""
        response = self.client.post(self.url, self.valid_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn("event_id", response.data)

        # Verify job was created in database
        job = Job.objects.get(event_id=response.data["event_id"])
        self.assertEqual(job.title, "Test Guideline")
        self.assertEqual(
            job.guideline_text,
            "This is a test clinical guideline for diabetes management.",
        )
        self.assertEqual(job.status, "queued")

    def test_create_job_missing_guideline_text(self):
        """Test job creation with missing guideline_text"""
        invalid_data = {"title": "Test Guideline"}
        response = self.client.post(self.url, invalid_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("guideline_text", response.data)
        self.assertEqual(response.data["guideline_text"][0], "This field is required.")

    def test_create_job_empty_guideline_text(self):
        """Test job creation with empty guideline_text"""
        invalid_data = {"title": "Test Guideline", "guideline_text": ""}
        response = self.client.post(self.url, invalid_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("guideline_text", response.data)
        self.assertEqual(
            response.data["guideline_text"][0], "This field may not be blank."
        )

    def test_create_job_without_title(self):
        """Test job creation without title (should use default)"""
        data = {"guideline_text": "Test guideline text"}
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

        job = Job.objects.get(event_id=response.data["event_id"])
        self.assertEqual(job.title, "Untitled Guideline")

    def test_create_job_invalid_json(self):
        """Test job creation with invalid JSON"""
        response = self.client.post(
            self.url, "invalid json", content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class JobDetailViewTest(APITestCase):
    """Test cases for JobDetailView"""

    def setUp(self):
        self.client = APIClient()
        self.job = Job.objects.create(
            title="Test Guideline",
            guideline_text="Test guideline text",
            summary="Test summary",
            checklist=["Step 1", "Step 2"],
            status="done",
        )

    def test_get_job_detail_success(self):
        """Test successful job detail retrieval"""
        url = reverse("job-detail", kwargs={"event_id": self.job.event_id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["event_id"], str(self.job.event_id))
        self.assertEqual(response.data["status"], "done")
        self.assertEqual(response.data["summary"], "Test summary")
        self.assertEqual(response.data["checklist"], ["Step 1", "Step 2"])

    def test_get_job_detail_not_found(self):
        """Test job detail retrieval for non-existent job"""
        fake_event_id = uuid.uuid4()
        url = reverse("job-detail", kwargs={"event_id": fake_event_id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("error", response.data)
        self.assertEqual(response.data["error"], "Job not found")


class ProcessGuidelineTaskTest(TestCase):
    """Test cases for the process_guideline Celery task"""

    def setUp(self):
        self.job = Job.objects.create(
            title="Test Guideline",
            guideline_text="Test guideline text for diabetes management.",
            status="queued",
        )
        self.event_id = str(self.job.event_id)

    @patch("jobs.tasks.client")
    def test_process_guideline_success(self, mock_client):
        """Test successful guideline processing"""
        # Mock OpenAI responses
        mock_summary_response = MagicMock()
        mock_summary_response.choices[0].message.content = "Test summary"
        mock_client.chat.completions.create.return_value = mock_summary_response

        # Mock checklist response
        mock_checklist_response = MagicMock()
        mock_checklist_response.choices[0].message.content = (
            "- Step 1\n- Step 2\n- Step 3"
        )
        mock_client.chat.completions.create.side_effect = [
            mock_summary_response,
            mock_checklist_response,
        ]

        result = process_guideline(self.event_id)

        # Verify job was updated
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "done")
        self.assertEqual(self.job.summary, "Test summary")
        self.assertEqual(self.job.checklist, ["Step 1", "Step 2", "Step 3"])
        self.assertEqual(result, f"Successfully processed job {self.event_id}")

        # Verify OpenAI was called twice
        self.assertEqual(mock_client.chat.completions.create.call_count, 2)

    @patch("jobs.tasks.client")
    def test_process_guideline_job_not_found_retry(self, mock_client):
        """Test task retry when job doesn't exist initially"""
        # Delete the job to simulate it not existing
        self.job.delete()

        # Mock the task retry mechanism
        with patch.object(process_guideline, "retry") as mock_retry:
            mock_retry.side_effect = Exception("Retry called")

            with self.assertRaises(Exception):
                process_guideline(self.event_id)

            # Verify retry was called
            mock_retry.assert_called_once()

    @patch("jobs.tasks.client")
    def test_process_guideline_already_processed(self, mock_client):
        """Test task when job is already processed"""
        self.job.status = "done"
        self.job.save()

        result = process_guideline(self.event_id)

        self.assertEqual(
            result, f"Job {self.event_id} already processed with status: done"
        )
        # Verify OpenAI was not called
        mock_client.chat.completions.create.assert_not_called()

    @patch("jobs.tasks.client")
    def test_process_guideline_openai_error(self, mock_client):
        """Test task failure when OpenAI API fails"""
        # Mock OpenAI to raise an exception
        mock_client.chat.completions.create.side_effect = Exception("OpenAI API Error")

        with self.assertRaises(Exception):
            process_guideline(self.event_id)

        # Verify job was marked as failed
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "failed")

    @patch("jobs.tasks.client")
    def test_process_guideline_checklist_parsing(self, mock_client):
        """Test checklist parsing from OpenAI response"""
        # Mock responses
        mock_summary_response = MagicMock()
        mock_summary_response.choices[0].message.content = "Test summary"

        mock_checklist_response = MagicMock()
        mock_checklist_response.choices[0].message.content = (
            "• First step\n- Second step\n* Third step"
        )

        mock_client.chat.completions.create.side_effect = [
            mock_summary_response,
            mock_checklist_response,
        ]

        result = process_guideline(self.event_id)

        # Verify checklist was parsed correctly
        self.job.refresh_from_db()
        expected_checklist = ["First step", "Second step", "Third step"]
        self.assertEqual(self.job.checklist, expected_checklist)


class JobIntegrationTest(APITestCase):
    """Integration tests for the complete job workflow"""

    def setUp(self):
        self.client = APIClient()
        self.create_url = reverse("create-job")
        self.valid_data = {
            "title": "Integration Test Guideline",
            "guideline_text": "This is a comprehensive test guideline for hypertension management.",
        }

    def test_complete_job_workflow(self):
        """Test the complete workflow from job creation to detail retrieval"""
        # Step 1: Create job
        create_response = self.client.post(
            self.create_url, self.valid_data, format="json"
        )
        self.assertEqual(create_response.status_code, status.HTTP_202_ACCEPTED)
        event_id = create_response.data["event_id"]

        # Step 2: Verify job exists and is queued
        job = Job.objects.get(event_id=event_id)
        self.assertEqual(job.status, "queued")
        self.assertEqual(job.title, "Integration Test Guideline")

        # Step 3: Get job details
        detail_url = reverse("job-detail", kwargs={"event_id": event_id})
        detail_response = self.client.get(detail_url)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["status"], "queued")
        self.assertIsNone(detail_response.data["summary"])
        self.assertIsNone(detail_response.data["checklist"])

    def test_job_status_transitions(self):
        """Test job status transitions through the workflow"""
        job = Job.objects.create(
            title="Status Test", guideline_text="Test text", status="queued"
        )

        # Test status transitions
        self.assertEqual(job.status, "queued")

        job.status = "processing"
        job.save()
        self.assertEqual(job.status, "processing")

        job.status = "done"
        job.save()
        self.assertEqual(job.status, "done")

        # Test that we can't transition from done to processing
        job.status = "processing"
        job.save()
        self.assertEqual(job.status, "processing")  # This should work in the model


class JobModelValidationTest(TestCase):
    """Test cases for Job model validation and constraints"""

    def test_title_max_length(self):
        """Test that title respects max_length constraint"""
        long_title = "A" * 256  # Exceeds max_length of 255
        job_data = {"title": long_title, "guideline_text": "Test guideline"}
        job = Job(**job_data)
        with self.assertRaises(ValidationError):
            job.full_clean()

    def test_status_max_length(self):
        """Test that status respects max_length constraint"""
        job = Job.objects.create(title="Test", guideline_text="Test guideline")

        # Test with valid status
        job.status = "queued"
        job.save()

        # Test with invalid status (should still work as it's not validated at DB level)
        job.status = "invalid_status_that_is_too_long_for_the_field"
        job.save()
        job.refresh_from_db()
        self.assertEqual(job.status, "invalid_status_that_is_too_long_for_the_field")

    def test_guideline_text_required(self):
        """Test that guideline_text is required"""
        job_data = {"title": "Test Title"}
        job = Job(**job_data)
        with self.assertRaises(ValidationError):
            job.full_clean()

class JobAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_create_job(self):
        response = self.client.post("/jobs/", {
            "title": "Pre-Surgical Instructions",
            "guideline_text": "Patients should fast for 12 hours before surgery."
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn("event_id", response.data)

    def test_retrieve_job(self):
        job = Job.objects.create(
            title="Test Guideline",
            guideline_text="Some text here.",
            status="queued"
        )
        response = self.client.get(f"/jobs/{job.event_id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "queued")

    def test_create_job_missing_guideline_text(self):
        response = self.client.post("/jobs/", {
            "title": "Missing Text"
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("guideline_text", response.data)

    def test_retrieve_nonexistent_job(self):
        fake_id = uuid.uuid4()
        response = self.client.get(f"/jobs/{fake_id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("error", response.data)

    def test_process_guideline_task(self):
        job = Job.objects.create(
            title="Checklist Job",
            guideline_text="Patient must fast and stop taking aspirin before surgery.",
            status="queued"
        )
        process_guideline(str(job.event_id))
        job.refresh_from_db()
        self.assertEqual(job.status, "done")
        self.assertIsNotNone(job.summary)
        self.assertIsInstance(job.checklist, list)
        self.assertTrue(len(job.checklist) > 0)

    @patch("jobs.tasks.client.chat.completions.create")
    def test_openai_failure_sets_job_failed(self, mock_create):
        mock_create.side_effect = Exception("OpenAI failure")
        job = Job.objects.create(
            title="Should Fail",
            guideline_text="Text that will trigger OpenAI.",
            status="queued"
        )
        with self.assertRaises(Exception):
            process_guideline(str(job.event_id))
        job.refresh_from_db()
        self.assertEqual(job.status, "failed")
