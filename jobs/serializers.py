from rest_framework import serializers


class JobCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a new guideline processing job.

    Validates the input data for job creation, ensuring required fields
    are present and properly formatted.
    """

    title: serializers.CharField = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="Optional title for the guideline",
    )
    guideline_text: serializers.CharField = serializers.CharField(
        required=True,
        allow_blank=False,
        help_text="The clinical guideline text to process",
    )
