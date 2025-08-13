# bcap/middleware/vite_inject.py  (only the DEV branch changed)

import os, re, json
from pathlib import Path
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

VITE_BASE = "/bcap/static"

BASE_DIR = Path(settings.BASE_DIR).resolve()

SEARCH_ROOTS = [
    (BASE_DIR / "bcap").resolve(),  # nr-bcap
    (BASE_DIR / ".." / "bcgov-arches-common" / "bcgov_arches_common").resolve(),
    (BASE_DIR / ".." / "arches" / "arches" / "app").resolve(),
]
MANIFEST_PATH = BASE_DIR / "bcap" / "staticfiles" / "dist" / "manifest.json"
EXTS = ["", ".js", ".ts", ".mjs", ".jsx", ".tsx", ".vue"]

ENTRY_MAP = {
    "/bcap/search": "media/js/views/search.js",
}
DEFAULT_ENTRY = "media/js/viewmodels/bcap-site.js"

SCRIPT_BUILD_RE = re.compile(
    r'<script[^>]+src="(?:/bcap/static/)?(?:js|chunks)/[^"]+\.js"[^>]*>\s*</script>',
    re.IGNORECASE,
)
LINK_BUILD_RE = re.compile(
    r'<link[^>]+href="(?:/bcap/static/)[^"]+\.css"[^>]*>',
    re.IGNORECASE,
)


def _find_entry_abs(rel_entry: str) -> Path | None:
    rel = rel_entry.lstrip("/")
    candidates = []
    for root in SEARCH_ROOTS:
        base = root / rel
        candidates.append(base)
        candidates.extend(root / (rel + ext) for ext in EXTS if ext)
        for ext in EXTS:
            if ext:
                candidates.append(root / rel / ("index" + ext))
    for p in candidates:
        if p.is_file():
            return p.resolve()
    return None


def _read_manifest():
    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def _vendor_tags_for_dev() -> str:
    """
    Classic scripts (non-module) so load order is guaranteed and they attach to window:
      1) jQuery
      2) Underscore (Backbone depends on it)
      3) Backbone (then wire Backbone.$)
      4) Bootstrap 3 JS (needs global jQuery)
      5) DataTables core + Bootstrap + Buttons + Responsive adapters (in order)
    All are served via Vite's @fs path so dev server can read them.
    """
    nm = "/@fs" + str((BASE_DIR / "node_modules").resolve()).replace("\\", "/")
    paths = [
        f"{VITE_BASE}{nm}/jquery/dist/jquery.min.js",
        f"{VITE_BASE}{nm}/underscore/underscore-min.js",
        f"{VITE_BASE}{nm}/backbone/backbone-min.js",
        # Wire Backbone to use the global jQuery
        "<script>window.Backbone && (window.Backbone.$ = window.jQuery || window.$);</script>",
        f"{VITE_BASE}{nm}/bootstrap/dist/js/bootstrap.min.js",
        # DataTables core first, then Bootstrap/Buttons/Responsive layers
        f"{VITE_BASE}{nm}/datatables.net/js/jquery.dataTables.min.js",
        f"{VITE_BASE}{nm}/datatables.net-bs/js/dataTables.bootstrap.min.js",
        f"{VITE_BASE}{nm}/datatables.net-buttons/js/dataTables.buttons.min.js",
        f"{VITE_BASE}{nm}/datatables.net-buttons-bs/js/buttons.bootstrap.min.js",
        f"{VITE_BASE}{nm}/datatables.net-responsive/js/dataTables.responsive.js",
        f"{VITE_BASE}{nm}/datatables.net-responsive-bs/js/responsive.bootstrap.js",
        # Optional: expose jQuery on window if some plugins check one or the other
        "<script>window.$ = window.$ || window.jQuery;</script>",
    ]
    # Wrap raw strings with <script> if they aren't already
    out = []
    for p in paths:
        if p.startswith("<script"):
            out.append(p)
        else:
            out.append(f'<script src="{p}"></script>')
    return "\n".join(out)


class ViteInjectMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        ctype = response.get("Content-Type", "")
        if "text/html" not in ctype or not hasattr(response, "content"):
            return response

        entry_rel = DEFAULT_ENTRY
        for prefix, src in ENTRY_MAP.items():
            if request.path.startswith(prefix):
                entry_rel = src
                break

        html = response.content.decode("utf-8", errors="ignore")

        if settings.DEBUG:
            # strip old build tags
            html = SCRIPT_BUILD_RE.sub("", html)
            html = LINK_BUILD_RE.sub("", html)

            abs_entry = _find_entry_abs(entry_rel)
            if not abs_entry:
                response.content = html.encode("utf-8")
                return response

            vendor_tags = _vendor_tags_for_dev()
            dev_tags = (
                vendor_tags
                + "\n"
                + f'<script type="module" src="{VITE_BASE}/@vite/client"></script>\n'
                f'<script type="module" src="{VITE_BASE}/@fs{abs_entry}"></script>'
            )

            if "</head>" in html:
                html = html.replace("</head>", dev_tags + "\n</head>")
            elif "</body>" in html:
                html = html.replace("</body>", dev_tags + "\n</body>")
            else:
                html += dev_tags

            response.content = html.encode("utf-8")
            response["Cache-Control"] = "no-store"
            response["Content-Length"] = str(len(response.content))
            return response

        # ---- production path (unchanged) ----
        manifest = _read_manifest()
        if not manifest:
            return response
        item = manifest.get(entry_rel) or next(
            (
                v
                for k, v in manifest.items()
                if k.endswith("/" + entry_rel) or k == entry_rel
            ),
            None,
        )
        if not item:
            return response
        tags = [f'<script type="module" src="{VITE_BASE}/{item["file"]}"></script>']
        for css in item.get("css", []):
            tags.append(f'<link rel="stylesheet" href="{VITE_BASE}/{css}">')
        for dep in item.get("imports", []):
            dep_item = manifest.get(dep)
            if dep_item:
                tags.append(
                    f'<link rel="modulepreload" href="{VITE_BASE}/{dep_item["file"]}">'
                )
        prod_tags = "\n".join(tags)
        if "</head>" in html:
            html = html.replace("</head>", prod_tags + "\n</head>")
        elif "</body>" in html:
            html = html.replace("</body>", prod_tags + "\n</body>")
        else:
            html += prod_tags
        response.content = html.encode("utf-8")
        response["Content-Length"] = str(len(response.content))
        return response
