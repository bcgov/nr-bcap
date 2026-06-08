"""Shared view mixins for BCAP resource APIs."""


class UserOwnedResourceMixin:
    """Restrict the resource queryset to instances created by the requesting user.

    Filters on the Arches `principaluser` (the creating user), so a detail GET
    for a resource the user doesn't own returns 404 rather than another user's
    data. Must precede arches_querysets' ArchesModelAPIMixin in the MRO so its
    get_queryset is the one being extended.
    """

    def get_queryset(self):
        return super().get_queryset().filter(principaluser=self.request.user)
