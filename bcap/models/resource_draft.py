import uuid

from django.conf import settings
from django.db import models


class ResourceDraft(models.Model):
    """A user's unvalidated, in-progress form state for a graph, as one JSON
    blob. The real resource is created and validated only on submit, so a draft
    can hold data the resource schema would reject (e.g. blank required fields)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="resource_drafts",
    )
    graph_slug = models.CharField(max_length=255)
    # Graph version authored against; stamped on create to detect stale drafts.
    graph_publication_id = models.UUIDField(null=True, blank=True)
    frontend_version = models.CharField(max_length=50, null=True, blank=True)
    # Set when drafting edits to an existing resource; null for a new one.
    resourceinstanceid = models.UUIDField(null=True, blank=True)
    # Section-keyed form state. Files are held by reference (file_id + metadata
    # via Arches' /temp_file), not value -- see resource_draft_api docstring.
    data = models.JSONField(default=dict)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bcap_resource_drafts"
        verbose_name = "Resource Draft"
        verbose_name_plural = "Resource Drafts"
        indexes = [models.Index(fields=["user", "graph_slug"])]

    def __str__(self):
        return f"{self.graph_slug} draft for {self.user} ({self.id})"
