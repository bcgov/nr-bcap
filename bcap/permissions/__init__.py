"""Who may reach what, in three layers, asked in this order.

1. applicant_gate: middleware refusing applicants the arches ecosystem's own
   routes, since most of them answer without asking anyone.
2. route_guards: the role a BCAP endpoint requires before it runs at all.
3. bcap_arches_permission_framework: the per-resource answer, installed as
   PERMISSION_FRAMEWORK, narrowed for applicants by permit_resource_access.

permission_settings holds the graph grants layer 3 starts from, and groups the
role names all three are written in.
"""
