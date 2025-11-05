from arches.app.views.resource import ResourceReportView as ResourceReportViewCore
from arches.app.views.resource import ResourceEditLogView as ResourceEditLogViewCore
from arches.app.utils.decorators import group_required
from django.utils.decorators import method_decorator
from arches.app.models import models
from arches.app.models.system_settings import settings
from django.shortcuts import render
from django.utils.translation import gettext as _
from arches.app.models.resource import Resource


@method_decorator(group_required("Resource Editor"), name="dispatch")
class ResourceReportView(ResourceReportViewCore):
    def get(self, request, resourceid=None):
        return super().get(request, resourceid)


class ResourceEditLogView(ResourceEditLogViewCore):
    def get(
        self, request, resourceid=None, view_template="views/resource/edit-log.htm"
    ):
        transaction_id = request.GET.get("transactionid", None)

        if resourceid is None:
            if transaction_id:
                recent_edits = models.EditLog.objects.filter(
                    transactionid=transaction_id
                ).order_by("-timestamp")
            else:
                recent_edits = (
                    models.EditLog.objects.all()
                    .exclude(resourceclassid=settings.SYSTEM_SETTINGS_RESOURCE_MODEL_ID)
                    .order_by("-timestamp")[:1000]
                )

            edited_ids = list({edit.resourceinstanceid for edit in recent_edits})

            resources = Resource.objects.filter(
                resourceinstanceid__in=edited_ids
            ).select_related("graph")

            edit_type_lookup = {
                "create": _("Resource Created"),
                "delete": _("Resource Deleted"),
                "tile delete": _("Tile Deleted"),
                "tile create": _("Tile Created"),
                "tile edit": _("Tile Updated"),
                "delete edit": _("Edit Deleted"),
                "bulk_create": _("Resource Created"),
                "update_resource_instance_lifecycle_state": _(
                    "Resource Lifecycle State Updated"
                ),
            }

            deleted_instances = [
                e.resourceinstanceid for e in recent_edits if e.edittype == "delete"
            ]

            graph_name_lookup = {
                str(r.resourceinstanceid): r.graph.name for r in resources
            }

            for edit in recent_edits:
                edit.friendly_edittype = edit_type_lookup[edit.edittype]
                edit.resource_model_name = None
                edit.deleted = edit.resourceinstanceid in deleted_instances

                if edit.resourceinstanceid in graph_name_lookup:
                    edit.resource_model_name = graph_name_lookup[
                        edit.resourceinstanceid
                    ]

                edit.displayname = edit.note

                if edit.resource_model_name is None:
                    try:
                        edit.resource_model_name = models.GraphModel.objects.get(
                            pk=edit.resourceclassid
                        ).name
                    except Exception:
                        pass

            context = self.get_context_data(
                main_script="views/edit-history", recent_edits=recent_edits
            )

            context["nav"]["title"] = _("Recent Edits")

            return render(request, "views/edit-history.htm", context)
        else:
            return super().get(request, resourceid, view_template)
