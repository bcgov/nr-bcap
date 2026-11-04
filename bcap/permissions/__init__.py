"""Who may reach what.

Two gates run first, knowing nothing about any one resource:

1. applicant_gate: middleware refusing applicants the arches ecosystem's own
   routes, since most of them answer without asking anyone.
2. route_guards: the role a BCAP endpoint requires before it runs at all.

Past those the question is per resource and permit_access answers it,
reached two ways that have to agree: through bcap_arches_permission_framework,
installed as PERMISSION_FRAMEWORK, for anything that asks arches; and directly,
for a view gating one resource or a list filtering a queryset. The framework
cannot serve both, since it answers one resource at a time and offers nothing
queryset shaped to narrow a list with.

The direct callers are the services, which is where the filtering belongs: one
that lists owns a base_query already carrying it, so a view never assembles the
rules itself and every route onto a graph narrows the same way; one gating a
single resource calls require_view or require_change before the fetch, so an
unreachable id answers 403 rather than an empty 404. A view filtering a queryset
of its own is the shape to distrust.

permission_settings holds the graph grants the framework starts from, and groups
the role names all of these are written in.
"""
