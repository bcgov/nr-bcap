"""Clone the process-requirement templates into working copies. Process
Requirements have no public POST; this is that create hook.

The templates (is_template_requirement=True) are assumed to already exist. Each
is structurally copied -- every tile rebuilt with fresh GUIDs, the same node
data, and parent links rewired -- into an independent is_template_requirement=
False working copy (a snapshot, with no link back to the template) to attach to
a new permit. The frontend fills in the values afterward by PATCH/PUT-ing the
working copy directly."""

from copy import deepcopy

from django.db import transaction

from arches.app.models.resource import Resource
from arches.app.models.tile import Tile

from arches_querysets.models import ResourceTileTree

from bcap.util.aliases.process_requirement import ProcessRequirementAliases as aliases
from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.graph import get_node
from bcap.util.i18n import localized_string


class ProcessRequirementService:
    # The process-requirement templates, in flow order.
    _TEMPLATE_NAMES = ["Recommend Referral", "Recommend Decision", "Decision Summary"]

    def create_working_copies(self):
        """An is_template_requirement=False working copy of each template, in
        flow order, to attach to a new permit application."""
        templates = self._templates_by_name()
        return [self.clone(templates[name]) for name in self._TEMPLATE_NAMES]

    def clone_by_id(self, template_id):
        """A working copy of the template with the given resourceinstanceid."""
        return self.clone(Resource.objects.get(pk=template_id))

    def clone(self, template):
        """A working copy of the template: every tile copied with a fresh GUID
        and the template flag cleared, so the copy is a real, editable
        requirement rather than another template."""
        source = Resource.objects.get(pk=template.pk)
        source.load_tiles()
        copy = self._copy_resource(source)
        self._clear_template_flag(copy)
        with transaction.atomic():
            super(Resource, copy).save()
            Tile.objects.bulk_create(copy.tiles)
        # Baseline descriptor so the copy is never descriptor-less when a
        # permit compiles its display; the clone hook re-saves it with the link.
        copy.save_descriptors()
        return copy

    @staticmethod
    def _copy_resource(source):
        """A new, unsaved resource with the source's tiles rebuilt under fresh
        GUIDs (from the model defaults), node data deep-copied, and parent links
        repointed at the new tiles."""
        # Built by hand instead of Resource.copy() because copy() is broken on
        # arches 8.1.x: it hardcodes save(context="copy"), so the *string*
        # "copy" reaches Resource.get_documents_to_index(), which does
        # `context["language"] = ...` assuming context is a dict and raises
        # This is fixed in Arches 8.2 by PR#12695
        new_resource = Resource()
        new_resource.graph = source.graph
        copies = {}
        for tile in source.tiles:
            new_tile = Tile()
            new_tile.data = deepcopy(tile.data)
            new_tile.nodegroup = tile.nodegroup
            new_tile.resourceinstance = new_resource
            new_tile.sortorder = tile.sortorder
            new_tile.tiles = []
            copies[tile.pk] = new_tile
        for tile in source.tiles:
            if tile.parenttile_id:
                copies[tile.pk].parenttile = copies[tile.parenttile_id]
        new_resource.tiles = list(copies.values())
        return new_resource

    def _templates_by_name(self):
        templates = ResourceTileTree.get_tiles(GraphSlugs.PROCESS_REQUIREMENT).filter(
            is_template_requirement=True
        )
        return {self._requirement_name(template): template for template in templates}

    @staticmethod
    def _requirement_name(requirement):
        identification = (
            requirement.aliased_data.requirement_identification.aliased_data
        )
        return localized_string(identification.requirement_name)

    def _clear_template_flag(self, resource):
        nodeid = str(
            get_node(GraphSlugs.PROCESS_REQUIREMENT, aliases.IS_TEMPLATE_REQUIREMENT).pk
        )
        for tile in resource.tiles:
            if nodeid in tile.data:
                tile.data[nodeid] = False
