#!/usr/bin/env python
"""Classify uploaded Archaeological Site and Site Visit documents against the
Archaeology ORCS (Schedule 170415) and the BCAP S3 retention design.

The ORCS schedules records by the file they belong to: "All the records in a
file are covered by the same retention schedule, regardless of media" ("How to
use" 2.10). A site record is the site inventory case file, 11300-35, which
includes the site's forms, maps and photographs, so every upload is 11300-35
(full retention) except contravention documents, 11100-30, and uploads with
a candidate series (below). The reason notes any exception.

Each upload's description, file name and type, and its section decide (file
contents are never read):
  * sensitivity-class, which picks the S3 bucket: human-remains, first-nations
    and site-location material go to Restricted. A missing description fails
    closed to Restricted.
  * candidate-orcs: another series it may belong in (a permit report copy, an
    AOA, a burial report). A lone FR candidate replaces the filed-in file in
    the tags; several candidates, or a DE one, leave it for the Records
    Officer.

The sheet includes each upload's file path and description for tracing it back.
Those can name the site and the document, so keep it somewhere restricted.

Run from the repo root, in the venv or the bcap container. It reads the PG*
settings from .env and queries Postgres directly, without starting Arches (if
host.docker.internal doesn't resolve outside Docker, prefix PGHOST=localhost):

    python3 tools/one_time/migration_classify_orcs_documents.py

It writes orcs-YYYY-MM-DD_HHMMSS.xlsx in tools/one_time.

    python3 tools/one_time/migration_classify_orcs_documents.py --rules

writes orcs-rules-YYYY-MM-DD.html instead: the rules below in plain English,
for the business to review. It holds no site data and needs no database.

    python3 tools/one_time/migration_classify_orcs_documents.py --rule-counts

prints how many uploads each rule matches, and nothing else, for tuning the
rules. Counts only, so the output is safe to share.

    python3 tools/one_time/migration_classify_orcs_documents.py --tag

writes each upload's tags (the s3-tags column) to its object in the S3 bucket,
replacing whatever tags it has. Needs the S3_* settings from .env as well.
Prints counts, and fileids with the S3 error code for any that fail.
"""

import os
import re
import sys
import time
from datetime import datetime

_START = time.monotonic()
HERE = os.path.dirname(os.path.abspath(__file__))


def step(name):
    """Print elapsed time for a step to stderr: timings only, no site data."""
    print(f"[{time.monotonic() - _START:6.1f}s] {name}", file=sys.stderr, flush=True)


# The Archaeology ORCS (Schedule 170415) is the source of truth; where the
# compliance mapping differs, the ORCS governs.
#
# Every upload here is in the site inventory case file (FR) except
# contravention documents, which are violation case files (FR). Site maps stay
# in 11300-35: the schedule says it "includes photographs, maps", and 11300-40
# is the province-wide map series arranged by NTS number. (The compliance
# mapping lists rendered site maps as 11300-40; it is wrong there.)
DEFAULT_SECONDARY = "11300-35"
CONTRAVENTION_SECONDARY = "11100-30"
# ORCS secondary -> (disposition-class, retention-trigger, retention-period),
# written to each upload's S3 tags. Both are "SO / nil / FR": kept while in
# use, no semi-active period, then fully retained by BC Archives.
#
# retention-trigger names the event that ends the SO (superseded or obsolete)
# period ("How to use" 2.7.1). The event belongs to the case file, so its date
# lives on the resource, not the object. With FR nothing is ever destroyed, so
# the trigger only marks when the file can transfer to BC Archives.
#   superseded-obsolete (11300-35): the schedule gives SO and no SO note, so
#     the trigger is the schedule's own term, "Superseded or Obsolete" (key of
#     terms, 2.7.1).
#   appeals-exhausted (11100-30): short for the schedule's SO note, "when final
#     decision has been made and any appeals exhausted and the file is no
#     longer required for trend analysis and research". All three must hold;
#     the name only covers the middle one.
RETENTION = {
    DEFAULT_SECONDARY: ("FR", "superseded-obsolete", "nil"),
    CONTRAVENTION_SECONDARY: ("FR", "appeals-exhausted", "nil"),
}

# ORCS secondaries the rules refer to: (title in the schedule, A, SA, FD).
SECONDARIES = {
    "11000-25": ("Archaeological Overview Assessment reports", "SO", "nil", "FR"),
    "11050-20": ("Aboriginal liaison case files", "SO", "nil", "FR"),
    "11100-30": ("Archaeological violation case files", "SO", "nil", "FR"),
    "11150-03": ("Burial reports", "SO", "nil", "FR"),
    "11150-20": ("Accidentally found human remains case files", "SO", "nil", "FR"),
    "11200-03": ("Archaeological permit reports", "SO", "nil", "FR"),
    "11200-30": ("Archaeological permit case files", "SO", "nil", "FR"),
    "11300-02": ("Archaeological site data requests", "SO", "10y", "DE"),
    "11300-30": (
        "Archaeological and heritage site designation case files",
        "SO",
        "nil",
        "FR",
    ),
    "11300-35": (
        "Archaeological and heritage site inventory case files",
        "SO",
        "nil",
        "FR",
    ),
}

# Text rules are (label, pattern, looks for); any one match applies. The label
# goes in classification-reason; "looks for" is the plain-English pattern for
# the rules document (--rules). Change both together.
# Animal words that mark bone as faunal. "non-human" counts as one.
ANIMAL = (
    r"(animals?|faunal?|non-? ?human|deer|elk|moose|caribou|bears?|dogs?|wolf|wolves"
    r"|beavers?|bison|goats?|sheep|seals?|sea lions?|whales?|salmon|fish|birds?|mammals?)"
)
UNLESS_ANIMAL = (
    ", unless the same text names an animal (deer, elk, fish, faunal, non-human...)"
    ' without saying "human"'
)


def unless_animal(pattern):
    """`pattern`, but not in a text that names an animal without also saying
    "human" (not "non-human")."""
    human = r"(?<!non-)(?<!non )\bhuman\b"
    return rf"^(?!(?=.*\b{ANIMAL}\b)(?!.*{human})).*?{pattern}"


RULES = {
    "sensitivity": {
        "human-remains": {
            "bucket": "Restricted",
            "about": "Human or ancestral remains and burials.",
            "text": [
                ("human remains", r"\bhuman remains\b", '"human remains"'),
                ("ancestral remains", r"\bancestral remains\b", '"ancestral remains"'),
                (
                    "skeletal",
                    unless_animal(r"\bskeletal\b"),
                    '"skeletal"' + UNLESS_ANIMAL,
                ),
                (
                    "human bone",
                    r"(?<!non-)(?<!non )\bhuman (bones?|skeletons?|skeletal|skulls?|teeth|tooth|crani(um|al)|mandibles?|femurs?|vertebra[el]?)\b",
                    '"human" followed by a bone word: bone, skeleton, skeletal, skull,'
                    " tooth, cranium, mandible, femur, vertebra",
                ),
                ("burial", r"\bburials?\b", '"burial" or "burials"'),
                ("interment", r"\binterment\b", '"interment"'),
                (
                    "osteology",
                    r"\bosteolog",
                    'words starting "osteolog" (osteology, osteological)',
                ),
                # Animal bone is common on sites ("deer mandible", "fish
                # vertebrae"), so these don't count when an animal is named.
                (
                    "skeletal terms",
                    unless_animal(
                        r"\b(cranium|cranial|mandible|femur|vertebra[el]?)\b"
                    ),
                    '"cranium", "cranial", "mandible", "femur", "vertebra", "vertebrae",'
                    ' "vertebral"' + UNLESS_ANIMAL,
                ),
                # The ORCS ties the coroner to found human remains
                # (11150-20), and a description that names the coroner is usually
                # the coroner's correspondence. Some letters clear bones as
                # non-human, but a wrong Restricted is cheap.
                ("coroner", r"\bcoroner\b", '"coroner"'),
            ],
        },
        "first-nations": {
            "bucket": "Restricted",
            "about": "Liaison and consultation records with First Nations.",
            "text": [
                (
                    "FN liaison",
                    r"\b(first nations?|aboriginal|indigenous) liaison\b",
                    '"First Nation(s) liaison", "Aboriginal liaison" or "Indigenous liaison"',
                ),
                (
                    "band council resolution",
                    r"\bband council resolution\b",
                    '"band council resolution"',
                ),
                (
                    "consultation",
                    r"\b(consultation|engagement) (record|log|summary)\b",
                    '"consultation" or "engagement" followed by "record", "log" or "summary"',
                ),
                ("capacity funding", r"\bcapacity funding\b", '"capacity funding"'),
                (
                    "consultation with a Nation",
                    r"\b(consultation|referral) (with|to) (the )?.{0,40}\bnation\b",
                    '"consultation" or "referral" with/to a "Nation" named within a few words',
                ),
            ],
        },
        "site-location": {
            "bucket": "Restricted",
            "about": (
                "Anything that shows or states where a site is. Text that states"
                " coordinates (a site form with UTMs) counts the same as a rendered map."
            ),
            "text": [
                (
                    "map",
                    r"\b(site (area |sketch )?)?maps?\b",
                    '"map", "maps", "site map", "site area map", "site sketch map"',
                ),
                ("site area", r"\bsite area\b", '"site area"'),
                ("rendering", r"\brendering\b", '"rendering"'),
                (
                    "air photo",
                    r"\b(air|aerial) ?photo(graph)?s?\b|\bortho ?photos?\b",
                    '"air photo", "aerial photograph", "orthophoto" and variants;'
                    " air photos show the site in its landscape",
                ),
                ("north arrow", r"\bnorth arrow\b", '"north arrow"'),
                (
                    "map scale",
                    r"\bscale\s*1\s*:\s*[\d,]+",
                    'a ratio scale such as "scale 1:20,000"',
                ),
                (
                    "CMT table (coordinates per tree)",
                    r"\b(cmts?|culturally modified trees?)\b.{0,40}?\b(tables?|inventory|inventories|data|list|spreadsheet|keys?)\b",
                    '"CMT" or "culturally modified tree(s)" followed closely by "table",'
                    ' "inventory", "data", "list", "spreadsheet" or "key";'
                    " these list coordinates per tree",
                ),
                (
                    "field notes (may hold sketch maps)",
                    r"\bfield ?(notes?|books?|notebooks?)\b",
                    '"field notes", "field book", "field notebook"; these often hold sketch maps',
                ),
                (
                    "shovel test log (coordinates per test)",
                    r"\b(shovel|subsurface)( test(s|ing)?)? (logs?|forms?|tables?|results|data|locations?)\b",
                    '"shovel" or "subsurface" (test/testing) followed by "log", "form",'
                    ' "table", "results", "data" or "locations"; these record coordinates per test',
                ),
                (
                    "UTM coordinates",
                    r"\b\d{6}(\.\d+)?\s*m?\s*e\b.{0,30}?\b\d{7}(\.\d+)?\s*m?\s*n\b",
                    "a 6-digit easting (E) followed by a 7-digit northing (N)",
                ),
                (
                    "coordinate terms",
                    r"\b(easting|northing|utm zone|nad ?83|nad ?27)\b",
                    '"easting", "northing", "UTM zone", "NAD83", "NAD27"',
                ),
                (
                    "lat/long",
                    r"\b[45]\d\.\d{4,}\b.{0,20}?-?1[1-3]\d\.\d{4,}\b",
                    "a decimal latitude in BC's range followed by a decimal longitude,"
                    " both to 4+ decimal places",
                ),
                (
                    "site form (records coordinates)",
                    r"\b(site (inventory |recording )?|recording )forms?\b",
                    '"site form", "site inventory form", "site recording form",'
                    ' "recording form"; these record coordinates',
                ),
            ],
            "upload": [
                (
                    "type starts with map",
                    lambda item: item["doc_type"].lower().startswith("map"),
                ),
                (
                    "type contains stratigraphy",
                    lambda item: "stratigraphy" in item["doc_type"].lower(),
                ),
                ("section is restricted", lambda item: item["section"] == "restricted"),
            ],
        },
        "general": {"bucket": "General", "about": "Nothing above matched."},
    },
    "no-description": "site-location",
    "candidate-orcs": {
        "11150-03": [
            ("burial report", r"\bburial report\b", '"burial report"'),
            (
                "osteology report",
                r"\bosteolog\w* (report|analysis)\b",
                '"osteology" or "osteological" followed by "report" or "analysis"',
            ),
        ],
        "11150-20": [
            (
                "found remains",
                r"\b(found|discovered|reported) human remains\b",
                '"found", "discovered" or "reported" human remains',
            ),
        ],
        "11050-20": [
            (
                "FN liaison",
                r"\b(first nations?|aboriginal) liaison\b",
                '"First Nation(s) liaison" or "Aboriginal liaison"',
            ),
        ],
        "11000-25": [
            (
                "overview assessment",
                r"\barchaeological overview assessment\b",
                '"archaeological overview assessment"',
            ),
            ("AOA", r"\baoa\b", '"AOA"'),
        ],
        # Permit reports, which the schedule says include AIAs. A copy kept on
        # the site for reference could instead be a site reference case file
        # (11300-45, DE), but reference copies aren't being considered for now:
        # they stay in the site file (11300-35, FR), the safer default since
        # nothing is destroyed.
        "11200-03": [
            (
                "impact assessment",
                r"\barchaeological impact assessment\b",
                '"archaeological impact assessment"',
            ),
            (
                "final report",
                r"\bfinal (permit )?report\b",
                '"final report" or "final permit report"',
            ),
        ],
        # Permit case files: the application and the permit itself.
        "11200-30": [
            (
                "heritage permit",
                r"\bheritage (inspection|investigation) permit\b",
                '"heritage inspection permit" or "heritage investigation permit"',
            ),
            (
                "alteration permit",
                r"\bsite alteration permit\b",
                '"site alteration permit"',
            ),
            (
                "permit no.",
                r"\bpermit (no\.?|number|#)\s*(19|20)\d\d[-_ ]\d{1,4}\b",
                '"permit no.", "permit number" or "permit #" followed by a number such as 2008-179',
            ),
        ],
        "11100-30": [
            ("contravention", r"\bcontravention\b", '"contravention"'),
            ("looting", r"\bloot(ing|ed)\b", '"looting" or "looted"'),
            ("stop work order", r"\bstop work order\b", '"stop work order"'),
            (
                "unauthorized alteration",
                r"\bunauthori[sz]ed (alteration|disturbance|excavation)\b",
                '"unauthorized" or "unauthorised" followed by "alteration",'
                ' "disturbance" or "excavation"',
            ),
        ],
        "11300-30": [
            ("designation order", r"\bdesignation order\b", '"designation order"'),
            (
                "heritage designation",
                r"\bprovincial heritage designation\b",
                '"provincial heritage designation"',
            ),
        ],
        "11300-02": [
            (
                "data request",
                r"\b(site )?data request\b",
                '"data request" or "site data request"',
            ),
        ],
    },
}

SENSITIVITY = RULES["sensitivity"]
RANK = {s: i for i, s in enumerate(SENSITIVITY)}


class RuleSet:
    """Regex rules per key; a key applies when any of its rules matches."""

    def __init__(self, rules):
        self.rules = {
            key: [(re.compile(p, re.I | re.S), label) for label, p, _ in patterns]
            for key, patterns in rules.items()
        }
        # One combined pattern per key: most texts match nothing, so one search
        # rules a key out instead of one search per rule.
        self.any = {
            key: re.compile("|".join(f"(?:{p})" for _, p, _ in patterns), re.I | re.S)
            for key, patterns in rules.items()
            if patterns
        }

    def match(self, texts):
        """{key: ["label in source", ...]} over {source: text}, for the keys
        with a matching rule."""
        result = {}
        for key, patterns in self.rules.items():
            hit = [
                src
                for src, text in texts.items()
                if key in self.any and self.any[key].search(text)
            ]
            if not hit:
                continue
            labels = [
                f"{label} in {src}"
                for rx, label in patterns
                for src in hit
                if rx.search(texts[src])
            ]
            if labels:
                result[key] = labels
        return result


class Classifier:
    """ORCS secondary from where the file is filed; sensitivity from its
    description, file name, upload type and section, failing closed
    when there is no description."""

    def __init__(self):
        self.sensitivity_rules = RuleSet(
            {key: rules.get("text", []) for key, rules in SENSITIVITY.items()}
        )
        self.candidate_rules = RuleSet(RULES["candidate-orcs"])

    @staticmethod
    def normalize(text):
        """Migrated descriptions use underscores and run words together
        (Site_Map, 2008_179_sitemap, ElRk_1_sitemap5.jpg); make them match the
        rules."""
        text = text.replace("_", " ")
        text = re.sub(r"(?<=[a-z])(?=\d)|(?<=\d)(?=[a-z])", " ", text, flags=re.I)
        return re.sub(r"(?i)sitemap", "site map", text)

    def texts(self, item):
        # Upload names are often descriptive too (ElRk_1_sitemap5.jpg).
        stem = os.path.splitext(os.path.basename(item["file_name"]))[0]
        return {
            "description": self.normalize(item["description"]),
            "file name": self.normalize(re.sub(r"[-.]", " ", stem)),
        }

    @staticmethod
    def signals(item, has_text):
        """(sensitivity, reason) from everything other than the text."""
        for key, rules in SENSITIVITY.items():
            for label, check in rules.get("upload", []):
                if check(item):
                    yield key, f"upload {label}"
        if not has_text:
            yield RULES["no-description"], "no description, fails closed"

    @staticmethod
    def review_tags(item, has_text, sensitivity, candidates):
        tags = []
        # The tile references a file id with no files row: no path, no S3 object.
        if not item["file_name"]:
            tags.append("no-file-record")
        if item["section"] == "restricted":
            tags.append("restricted-upload")
        if not has_text:
            tags.append("no-description")
        if sensitivity in ("human-remains", "first-nations"):
            tags.append(f"sensitive:{sensitivity}")
        if candidates:
            tags.append("candidate-orcs")
        if item["model"] == "site_visit":
            tags.append("placement:site-visit")
        return tags

    @staticmethod
    def record_tags(item, secondary, sensitivity, has_text):
        """The S3 tags, named and ordered as the live records storage writes
        them. With no description nothing decided the sensitivity, so it needs
        review, as a live upload no rule matches does."""
        disposition, trigger, period = Classifier.retention(secondary)
        return {
            "orcs-classification": secondary,
            "disposition-class": disposition,
            "retention-trigger": trigger,
            "retention-period": period,
            "sensitivity-class": sensitivity,
            "resource-instance-id": item["resourceinstanceid"],
            "classification-status": "auto" if has_text else "needs-review",
        }

    @staticmethod
    def retention(secondary):
        """(disposition, trigger, period). A secondary not in RETENTION takes its
        FD and SA from the schedule and the default trigger."""
        if secondary in RETENTION:
            return RETENTION[secondary]
        _, _, period, disposition = SECONDARIES[secondary]
        return disposition, "superseded-obsolete", period

    @staticmethod
    def tagged_secondary(item, filed, candidates):
        """A lone FR candidate replaces the filed-in file; a DE one doesn't.
        Several are logged and keep the filed-in file for the Records Officer."""
        if len(candidates) > 1:
            print(
                f"fileid {item['fileid']}: several candidates"
                f" ({';'.join(candidates)}), kept {filed}",
                file=sys.stderr,
                flush=True,
            )
            return filed
        if candidates and SECONDARIES[candidates[0]][3] == "FR":
            return candidates[0]
        return filed

    def classify(self, item):
        secondary = (
            CONTRAVENTION_SECONDARY
            if item["section"] == "contravention"
            else DEFAULT_SECONDARY
        )
        texts = self.texts(item)
        has_text = bool(texts["description"].strip())

        found = self.sensitivity_rules.match(texts)
        reasons = [(s, ", ".join(labels)) for s, labels in found.items()]
        reasons += self.signals(item, has_text)
        reasons.sort(key=lambda r: RANK[r[0]])
        sensitivity = reasons[0][0] if reasons else "general"

        cand_labels = self.candidate_rules.match(texts)
        candidates = sorted(c for c in cand_labels if c != secondary)
        tagged = self.tagged_secondary(item, secondary, candidates)

        # Nearly everything is the site file (DEFAULT_SECONDARY); only say so when not.
        why = (
            [f"{secondary}: filed in {item['section']}"]
            if secondary != DEFAULT_SECONDARY
            else []
        )
        why += [f"{s}: {reason}" for s, reason in reasons]
        if not reasons:
            why.append("general: no sensitive terms found")
        why += [
            f"{'tagged' if c == tagged else 'may be'} {c}: {', '.join(cand_labels[c])}"
            for c in candidates
        ]

        review = self.review_tags(item, has_text, sensitivity, candidates)

        tags = self.record_tags(item, tagged, sensitivity, has_text)
        return {
            **tags,
            "tags": tags,
            # Every value is a fixed code, a UUID or empty, so no URL-encoding.
            "s3-tags": "&".join(f"{k}={v}" for k, v in tags.items()),
            # The suggested file(s) when a hint matched, otherwise the file it's
            # filed in, so the column always names an ORCS secondary.
            "candidate-orcs": ";".join(candidates) or secondary,
            "review": ";".join(review),
            "classification-reason": "; ".join(why),
        }


class UploadInventory:
    """Reads the upload tiles and file paths straight from Postgres, without
    starting Arches (a one-time script, so it can rely on Arches' table and
    column names). Never touches the files themselves."""

    def __init__(self, conn):
        self.conn = conn
        self._nodes = {}

    # Upload sections per model: (section, file node, type node, description node).
    SHARED_SECTIONS = [
        (
            "related_documents",
            "related_site_documents",
            "related_document_type",
            "related_document_description",
        ),
        ("site_images", "site_images", "image_type", "image_description"),
    ]
    SECTIONS = {
        "archaeological_site": SHARED_SECTIONS
        + [
            ("contravention", "contravention_document", None, None),
            ("restricted", "restricted_document", None, None),
        ],
        "site_visit": SHARED_SECTIONS,
    }

    def node(self, graph_slug, alias):
        """(node id, nodegroup id) of a node on the published graph."""
        if (graph_slug, alias) not in self._nodes:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT n.nodeid::text, n.nodegroupid::text
                    FROM nodes n JOIN graphs g ON g.graphid = n.graphid
                    WHERE g.slug = %s AND n.alias = %s AND n.source_identifier IS NULL
                    LIMIT 1
                    """,
                    (graph_slug, alias),
                )
                row = cur.fetchone()
            if row is None:
                sys.exit(f"Node {alias!r} not found on graph {graph_slug!r}.")
            self._nodes[(graph_slug, alias)] = row
        return self._nodes[(graph_slug, alias)]

    @staticmethod
    def label(value):
        """First preferred label of a reference node value."""
        for item in value or []:
            for label in item.get("labels") or []:
                if label.get("valuetype_id") == "prefLabel":
                    return label.get("value") or ""
        return ""

    @staticmethod
    def string(value):
        if isinstance(value, dict):
            return next(
                (
                    v["value"]
                    for v in value.values()
                    if isinstance(v, dict) and v.get("value")
                ),
                "",
            )
        return value or ""

    def tiles(self, model, file_alias, type_alias, desc_alias):
        """(resource id, tile id, files, type, description) for the tiles holding
        an upload node. Only those three node values are read from each tile.
        Contravention and restricted uploads have no type or description node."""
        file_node, nodegroup = self.node(model, file_alias)
        type_node = self.node(model, type_alias)[0] if type_alias else None
        desc_node = self.node(model, desc_alias)[0] if desc_alias else None
        # A named (server-side) cursor streams the rows instead of loading them all.
        with self.conn.cursor(name=f"tiles_{model}_{file_alias}") as cur:
            cur.itersize = 5000
            cur.execute(
                """
                SELECT resourceinstanceid::text, tileid::text,
                       tiledata -> %s, tiledata -> %s, tiledata -> %s
                FROM tiles WHERE nodegroupid = %s
                """,
                (file_node, type_node, desc_node, nodegroup),
            )
            yield from cur

    def items(self):
        """One entry per file referenced from an upload tile, with the upload's
        type and description."""
        for model, sections in self.SECTIONS.items():
            for section, file_alias, type_alias, desc_alias in sections:
                tiles = self.tiles(model, file_alias, type_alias, desc_alias)
                for resource_id, tile_id, files, doc_type, description in tiles:
                    for entry in files or []:
                        if entry.get("file_id"):
                            yield {
                                "fileid": str(entry["file_id"]),
                                "resourceinstanceid": str(resource_id),
                                "tileid": str(tile_id),
                                "model": model,
                                "section": section,
                                "doc_type": self.label(doc_type),
                                "description": self.string(description),
                            }

    def paths(self, fileids):
        """{file id: path} for just these files, not the whole files table."""
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT fileid::text, path FROM files WHERE fileid = ANY(%s::uuid[])",
                (list(fileids),),
            )
            return dict(cur.fetchall())

    def uploads(self):
        """items() with each upload's file path filled in ("" when the file
        record is missing)."""
        items = list(self.items())
        step(f"read {len(items)} uploads from tiles")
        paths = self.paths({item["fileid"] for item in items})
        step(f"read {len(paths)} file paths")
        for item in items:
            item["file_name"] = paths.get(item["fileid"], "")
        return items


class OrcsReport:
    """Writes one sheet row per upload: trace columns plus the classification."""

    # Column -> width in characters.
    COLUMNS = {
        "fileid": 38,
        "orcs-classification": 20,
        "disposition-class": 17,
        "retention-trigger": 20,
        "retention-period": 16,
        "sensitivity-class": 16,
        "resource-instance-id": 38,
        "classification-status": 21,
        "resource-url": 60,
        "description": 50,
        "file-path": 50,
        "candidate-orcs": 18,
        "review": 40,
        "classification-reason": 80,
        "s3-tags": 80,
    }

    def __init__(self, inventory, classifier):
        self.inventory = inventory
        self.classifier = classifier

    def rows(self):
        # Same as bcap.util.links.app_url, read from .env instead of settings.
        base = os.environ.get("PUBLIC_SERVER_ADDRESS", "").rstrip("/")
        for item in self.inventory.uploads():
            yield {
                "fileid": item["fileid"],
                "resource-url": f"{base}/resource/{item['resourceinstanceid']}",
                "description": item["description"],
                "file-path": item["file_name"],
                **self.classifier.classify(item),
            }

    # Control characters Excel rejects; migrated descriptions can hold them.
    ILLEGAL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

    def write(self, out):
        # XlsxWriter is several times faster per cell than openpyxl.
        import xlsxwriter

        workbook = xlsxwriter.Workbook(
            out, {"strings_to_urls": False, "strings_to_numbers": False}
        )
        sheet = workbook.add_worksheet("ORCS")
        for i, width in enumerate(self.COLUMNS.values()):
            sheet.set_column(i, i, width)
        sheet.freeze_panes(1, 0)
        sheet.write_row(0, 0, list(self.COLUMNS))
        n = 0
        for n, row in enumerate(self.rows(), start=1):
            sheet.write_row(
                n, 0, [self.ILLEGAL.sub("", str(row[c])) for c in self.COLUMNS]
            )
        sheet.autofilter(0, 0, n, len(self.COLUMNS) - 1)
        workbook.close()


def load_env():
    """The repo's .env. Already-set environment variables win."""
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(HERE)), ".env"))


def connect():
    """Postgres connection from the same PG* variables the app uses, so
    PGHOST=localhost works."""
    import psycopg2

    load_env()
    return psycopg2.connect(
        host=os.environ["PGHOST"],
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ["PGDBNAME"],
        user=os.environ["PGUSERNAME"],
        password=os.environ["PGPASSWORD"],
    )


def s3_client():
    """S3 client set up like the app's default storage in bcap/settings.py."""
    import boto3
    from botocore.config import Config

    load_env()
    proxy = os.environ.get("S3_PROXIES")
    return boto3.client(
        "s3",
        endpoint_url="https://nrs.objectstore.gov.bc.ca/",
        aws_access_key_id=os.environ["S3_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["S3_SECRET_ACCESS_KEY"],
        config=Config(
            proxies={"https": proxy} if proxy else None, max_pool_connections=16
        ),
    )


# Untested against the real object store; only tried with a stubbed S3 client.
def tag_objects(inventory):
    """Writes each upload's tags to its S3 object, replacing any tags it has.
    Prints counts, and the fileid and S3 error code of each failure; no paths."""
    from concurrent.futures import ThreadPoolExecutor

    from botocore.exceptions import ClientError

    client, bucket = s3_client(), os.environ["S3_BUCKET"]
    classifier = Classifier()

    def tag(item):
        tags = classifier.classify(item)["tags"]
        try:
            client.put_object_tagging(
                Bucket=bucket,
                Key=item["file_name"],
                Tagging={"TagSet": [{"Key": k, "Value": v} for k, v in tags.items()]},
            )
        except ClientError as e:
            print(
                f"fileid {item['fileid']}: {e.response['Error']['Code']}",
                file=sys.stderr,
                flush=True,
            )
            return False
        return True

    uploads = inventory.uploads()
    # A tile can reference a file id with no files row, so no S3 object.
    items = [item for item in uploads if item["file_name"]]
    with ThreadPoolExecutor(max_workers=16) as pool:
        tagged = sum(pool.map(tag, items))
    print(
        f"{tagged} tagged, {len(items) - tagged} failed,"
        f" {len(uploads) - len(items)} skipped with no file record"
    )


def rule_counts(inventory):
    """Uploads each rule matches, and the resulting class totals. Counts only."""
    classifier = Classifier()
    groups = {
        **{
            ("sensitivity", k): v for k, v in classifier.sensitivity_rules.rules.items()
        },
        **{("candidate", k): v for k, v in classifier.candidate_rules.rules.items()},
    }
    hits = {(g, label): 0 for g, rules in groups.items() for _, label in rules}
    classes, total = {}, 0
    for item in inventory.uploads():
        total += 1
        texts = classifier.texts(item)
        for g, rules in groups.items():
            for rx, label in rules:
                hits[(g, label)] += any(rx.search(t) for t in texts.values())
        cls = classifier.classify(item)["sensitivity-class"]
        classes[cls] = classes.get(cls, 0) + 1

    print(f"{total} uploads")
    for cls, n in classes.items():
        print(f"  {cls}: {n}")
    print("\nuploads matched per rule")
    for g, rules in groups.items():
        if rules:
            print(f"{g[0]} {g[1]}")
        for _, label in rules:
            print(f"  {label}: {hits[(g, label)]}")


def main():
    if "--rule-counts" in sys.argv[1:]:
        rule_counts(UploadInventory(connect()))
        step("counted")
        return
    if "--tag" in sys.argv[1:]:
        tag_objects(UploadInventory(connect()))
        step("tagged")
        return
    if "--rules" in sys.argv[1:]:
        # The rules document holds no site data, so it can be shared; it
        # needs no database.
        from orcs_rules_doc import render

        out = os.path.join(HERE, f"orcs-rules-{datetime.now():%Y-%m-%d}.html")
        with open(out, "w", encoding="utf-8") as f:
            f.write(render(sys.modules[__name__]))
        print(f"Done. Rules in {out}")
        return
    out = os.path.join(HERE, f"orcs-{datetime.now():%Y-%m-%d_%H%M%S}.xlsx")
    OrcsReport(UploadInventory(connect()), Classifier()).write(out)
    step("classified and wrote the spreadsheet")
    print(f"Done. Results in {out}")


if __name__ == "__main__":
    main()
