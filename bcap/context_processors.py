from django.conf import settings


def vueEntrypointsForPath(request):
    return (
        settings.ENTRYPOINTS[request.path]
        if request.path in settings.ENTRYPOINTS
        else []
    )


def vite(request):
    print(request.path)
    return {
        "USE_VITE": getattr(settings, "USE_VITE", False),
        "VITE_BASE": getattr(settings, "VITE_BASE", "/bcap/@vite/"),
        "VUE_ENTRYPOINTS": vueEntrypointsForPath(request),
    }