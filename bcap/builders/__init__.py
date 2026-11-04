# Builders that create bcap graph resources through arches-querysets, so seeded
# and test data stays in sync with how the services read it. ResourceBuilder
# holds the generic primitives; the domain builders (contributor, process
# requirement) extend it, and the dashboard demo seeder composes them.
