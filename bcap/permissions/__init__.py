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

permission_settings holds the graph grants the framework starts from, and groups
the role names all of these are written in.
"""
