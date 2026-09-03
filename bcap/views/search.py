from arches.app.models.system_settings import settings
from arches.app.utils.response import JSONResponse
import arches.app.tasks as arches_tasks
import arches.app.utils.task_management as task_management
import arches.app.utils.zip as zip_utils
from arches.app.views.search import export_results as arches_export_results

from bcap.permissions.route_permissions import resource_exporter_only_function_view
from bcap.search.search_export import BCAPSearchResultsExporter
import bcap.tasks.tasks as bcap_tasks


# Overrides arches.app.views.search.export_results (registered first in bcap/urls.py).
# For tilecsv, uses BCAPSearchResultsExporter (adds UTF-8 BOM) instead of the base class.
# All other formats fall through to the Arches view unchanged.
@resource_exporter_only_function_view
def export_results(request):
    request.GET = request.GET.copy()
    for key, value in request.POST.items():
        request.GET[key] = value

    total = int(request.GET.get("total", 0))
    report_link = request.GET.get("reportlink", False)

    if request.GET.get("format", "tilecsv") == "tilecsv":
        if total <= settings.SEARCH_EXPORT_IMMEDIATE_DOWNLOAD_THRESHOLD:
            exporter = BCAPSearchResultsExporter(search_request=request)
            export_files, _ = exporter.export("tilecsv", report_link)
            return zip_utils.zip_response(
                export_files, zip_file_name=f"{settings.APP_NAME}_export.zip"
            )

        if task_management.check_if_celery_available():
            request_values = {**dict(request.GET), "path": request.get_full_path()}
            bcap_tasks.export_search_results.apply_async(
                (request.user.id, request_values, "tilecsv", report_link),
                link=arches_tasks.update_user_task_record.s(),
                link_error=arches_tasks.log_error.s(),
            )
            return JSONResponse(
                {
                    "success": True,
                    "message": _(
                        "{total} instances have been submitted for export. "
                        "Click the Bell icon to check for a link to download your data"
                    ).format(total=total),
                }
            )

    return arches_export_results(request)
