"""Render the classifier's rules as an HTML document for the business to review.

Run through the classifier, not directly:

    python3 tools/one_time/migration_classify_orcs_documents.py --rules

The rule tables come from RULES, SECONDARIES and RETENTION in
migration_classify_orcs_documents.py, so they can't drift from what runs. The
prose around them (how scoring works, trigger notes, open decisions) lives
here and has to be kept in step by hand.
"""

from html import escape

CLASS_NAMES = {
    "human-remains": "Human remains",
    "first-nations": "First Nations",
    "site-location": "Site location",
    "general": "General",
}

# What each retention trigger means, quoted from the schedule where it has an
# SO note. Keyed by the trigger name in RETENTION.
TRIGGER_NOTES = {
    "superseded-obsolete": "the schedule's own term, Superseded or Obsolete; it gives no more specific event for this series.",
    "appeals-exhausted": (
        "decision final, appeals exhausted, and no longer needed for trend analysis"
        " and research (all three)."
    ),
}

DECISIONS = [
    ("Approve the rules", "Confirm the terms and classes, or mark changes."),
    (
        "Coordinates in text",
        "Should site forms, UTMs and lat/long count as Restricted like a map?"
        " (Compliance mapping, Open Decision 1.)",
    ),
]

CSS = """
:root {
  --bg: #f6f7f8; --surface: #ffffff; --fg: #1c2328; --muted: #5a6670; --line: #d9dee2;
  --accent: #1f5c63; --accent-soft: #e3eef0;
  --restricted: #8a2f22; --restricted-soft: #f6e5e1;
  --general: #33603d; --general-soft: #e4f0e6;
  --font-display: "Literata", Georgia, "Times New Roman", serif;
  --font-body: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --font-mono: "IBM Plex Mono", ui-monospace, Menlo, monospace;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #12171a; --surface: #192024; --fg: #e3e8eb; --muted: #9aa7b0; --line: #2c363c;
    --accent: #7cc2c9; --accent-soft: #1d3236;
    --restricted: #e79a8c; --restricted-soft: #3a2320;
    --general: #93cf9e; --general-soft: #1f3324;
    color-scheme: dark;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg); font-family: var(--font-body); font-size: 16px; line-height: 1.6; }
.page { max-width: 900px; margin: 0 auto; padding-inline: 20px; padding-block: 36px 56px; display: grid; gap: 32px; }
header { display: grid; gap: 6px; border-bottom: 1px solid var(--line); padding-bottom: 16px; }
h1, h2, h3 { font-family: var(--font-display); font-weight: 650; text-wrap: balance; line-height: 1.2; margin: 0; }
h1 { font-size: clamp(26px, 4vw, 32px); }
h2 { font-size: 24px; }
h3 { font-size: 18px; font-weight: 500; }
p { margin: 0; max-width: 68ch; }
section { display: grid; gap: 16px; }
code { font-family: var(--font-mono); font-size: 0.9em; }
ul, ol { margin: 0; padding-left: 1.3em; display: grid; gap: 6px; max-width: 68ch; }
.table-wrap { overflow-x: auto; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); }
table { border-collapse: collapse; width: 100%; font-size: 14.5px; }
th, td { text-align: left; vertical-align: top; padding: 10px 14px; border-bottom: 1px solid var(--line); }
tr:last-child td { border-bottom: 0; }
th { font-size: 12px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); background: var(--bg); }
td.num { font-family: var(--font-mono); font-variant-numeric: tabular-nums; white-space: nowrap; }
.pill { display: inline-block; font-family: var(--font-mono); font-size: 12px; font-weight: 500; padding: 1px 8px; border-radius: 999px; white-space: nowrap; }
.pill.Restricted { background: var(--restricted-soft); color: var(--restricted); }
.pill.General { background: var(--general-soft); color: var(--general); }
.rules { list-style: none; padding: 0; margin: 0; display: grid; gap: 6px; }
.rules li { display: grid; grid-template-columns: auto 1fr; gap: 8px; align-items: baseline; }
.note { font-size: 14.5px; color: var(--muted); }
.decisions { list-style: none; padding: 0; max-width: none; display: grid; gap: 12px; }
.decisions li { background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 14px 18px; display: grid; gap: 4px; }
.d-id { font-family: var(--font-mono); font-size: 12.5px; color: var(--accent); font-weight: 500; margin-right: 10px; }
footer { border-top: 1px solid var(--line); padding-top: 18px; font-size: 13.5px; color: var(--muted); }
"""

FONTS = (
    "https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500"
    "&family=IBM+Plex+Sans:wght@400;500;600&family=Literata:opsz,wght@7..72,500;7..72,650"
    "&display=swap"
)


def bullets(items):
    return (
        '<ul class="rules">' + "".join(f"<li>{escape(i)}</li>" for i in items) + "</ul>"
    )


def table(headers, rows):
    head = "".join(f"<th>{escape(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(rows_cells) + "</tr>" for rows_cells in rows)
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def secondary_title(code, secondaries):
    title, *_ = secondaries.get(code, ("(not in SECONDARIES)",))
    return title


def render(mod):
    """HTML for the rules in the classifier module `mod`."""
    rules, secondaries, retention = mod.RULES, mod.SECONDARIES, mod.RETENTION
    sensitivity = rules["sensitivity"]
    fallback = CLASS_NAMES.get(rules["no-description"], rules["no-description"])

    retention_rows = []
    for code, (fd, trigger, period) in retention.items():
        title, a, sa, _ = secondaries[code]
        upload = (
            "Uploaded to the contravention section"
            if code == mod.CONTRAVENTION_SECONDARY
            else "Everything else"
        )
        retention_rows.append(
            [
                f"<td>{upload}</td>",
                f'<td class="num">{code}</td>',
                f"<td>{escape(title)}</td>",
                f'<td class="num">{a} / {sa} / {fd}</td>',
                f"<td><code>{escape(trigger)}</code>: {escape(TRIGGER_NOTES.get(trigger, ''))}</td>",
            ]
        )

    class_rows = [
        [
            f"<td><b>{CLASS_NAMES.get(key, key)}</b><br>"
            f'<span class="pill {c["bucket"]}">{c["bucket"]}</span></td>',
            f"<td>{escape(c.get('about', ''))}</td>",
            "<td>"
            + bullets(
                [looks_for for _, _, looks_for in c.get("text", [])]
                + [
                    f"upload {label}, whatever the text says"
                    for label, _ in c.get("upload", [])
                ]
            )
            + "</td>",
        ]
        for key, c in sensitivity.items()
        if c.get("text") or c.get("upload")
    ]

    candidate_rows = []
    for key, crules in rules["candidate-orcs"].items():
        codes = key.split("|")
        titles = " <i>or</i> ".join(
            f"{escape(secondary_title(c, secondaries))} ({secondaries.get(c, ('', '', '', '?'))[3]})"
            for c in codes
        )
        raised = [looks_for for _, _, looks_for in crules]
        candidate_rows.append(
            [
                f'<td class="num">{"<br>or ".join(codes)}</td>',
                f"<td>{titles}</td>",
                f"<td>{bullets(raised)}</td>",
            ]
        )

    decisions = "".join(
        f'<li><div><span class="d-id">D{i}</span><b>{escape(t)}</b></div><p>{escape(d)}</p></li>'
        for i, (t, d) in enumerate(DECISIONS, start=1)
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ORCS Upload Classification Rules for current files imported from HRIA</title>
<link rel="stylesheet" href="{FONTS}">
<style>{CSS}</style>
</head>
<body>
<div class="page">
  <header>
    <h1>ORCS Upload Classification Rules for current files imported from HRIA</h1>
  </header>

  <p>For each upload to a site or site visit, the classifier reads only the <b>description</b> and <b>file name</b>, plus the <b>document type</b> and <b>upload section</b> for a few rules. It <b>never opens the file</b>, so a document's contents can't change the result. It recommends an ORCS file, a sensitivity class, and any other ORCS files worth checking, and changes nothing. The Archaeology ORCS (Schedule 170415) is the source of truth.</p>

  <section>
    <h2>1. ORCS file and retention</h2>
    <p>ORCS files a record by the file it sits in, regardless of media (How to Use ORCS, 2.10), so site uploads go in the site inventory case file.</p>
    {table(["Upload", "Secondary", "Title", "A / SA / FD", "Retention trigger"], retention_rows)}
    <p class="note">SO = kept while in use, until the trigger; FR = full retention, transferred to BC Archives and never destroyed; DE = destroyed.</p>
  </section>

  <section>
    <h2>2. Sensitivity</h2>
    <p>Each upload is tagged with a sensitivity class. Human remains, First Nations and site location are <b>Restricted</b>: every read is logged, and a tag-based access policy on the bucket can narrow who may read them. Anything that matches none of them is <b>General</b>.</p>
    <p class="note">The most sensitive matching class wins. No description means {fallback.lower()}.</p>
    {table(["Class", "Covers", "Looks for (any one is enough)"], class_rows)}
  </section>

  <section>
    <h2>3. Other possible ORCS files</h2>
    {table(["Secondary", "Title in the schedule", "Raised by"], candidate_rows)}
    <p class="note">When exactly one of these matches and it is FR, it replaces the site file in the upload's ORCS tag, with the schedule's default trigger, Superseded or Obsolete. Several matches, or a DE one, keep the site file and are flagged for review.</p>
    <p class="note">A permit report copy kept on a site could be a site reference case file (11300-45, DE). That option isn't used for now: copies stay in the site file (11300-35, FR), so nothing is destroyed.</p>
  </section>

  <section>
    <h2>Decisions needed</h2>
    <ol class="decisions">{decisions}</ol>
  </section>

  <footer>
    Sources: Archaeology ORCS Schedule 170415 (Amendment 1); BCAP S3 Compliance Mapping rev. 2. Rule tables are generated from the classifier code.
  </footer>
</div>
</body>
</html>
"""
