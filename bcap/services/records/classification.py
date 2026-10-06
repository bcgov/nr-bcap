"""ORCS classification of uploads, as S3 tags.

Reads only the upload node, document type and file extension, never
descriptions or file names. Anything the tables don't cover fails closed to
site-location.
"""

import logging
import uuid
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import NamedTuple

from arches.app.models.models import File, Node, TileModel
from arches_controlled_lists.datatypes.datatypes import ReferenceDataType

from bcap.util.aliases.archaeological_site import ArchaeologicalSiteAliases as Site
from bcap.util.aliases.site_visit import SiteVisitAliases as Visit
from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.dicts import kebab_case_keys

logger = logging.getLogger(__name__)


class Sensitivity(StrEnum):
    """Most sensitive first. Anything but general is restricted."""

    HUMAN_REMAINS = "human-remains"
    FIRST_NATIONS = "first-nations"
    SITE_LOCATION = "site-location"
    GENERAL = "general"


class Status(StrEnum):
    AUTO = "auto"
    NEEDS_REVIEW = "needs-review"  # no rule decides its sensitivity
    UNCLASSIFIED = "unclassified"  # unknown upload node


class OrcsFile(NamedTuple):
    """A Schedule 170415 file number (primary-secondary) and its retention."""

    number: str
    disposition: str  # FR, SR or DE (How to Use ORCS, 2.7.2)
    retention_trigger: str  # the event that ends the SO period
    retention_period: str = "nil"


class UploadNode(NamedTuple):
    orcs: OrcsFile
    type_alias: str | None = None  # its document type node
    sensitivity: Sensitivity | None = None  # fixed, whatever the type


@dataclass(frozen=True)
class RecordTags:
    """An upload's S3 tags. The defaults fail closed. S3 allows at most 10."""

    orcs_classification: str = ""
    disposition_class: str = ""
    retention_trigger: str = ""
    retention_period: str = ""
    sensitivity_class: Sensitivity = Sensitivity.SITE_LOCATION
    resource_instance_id: str = ""
    classification_status: Status = Status.UNCLASSIFIED

    def as_s3(self):
        return {k: str(v) for k, v in kebab_case_keys(asdict(self)).items()}


class ClassificationService:
    SITE_INVENTORY = OrcsFile("11300-35", "FR", "superseded-obsolete")
    # The trigger is short for its SO note: decision final, appeals exhausted
    # and no longer needed for research.
    VIOLATION_CASE = OrcsFile("11100-30", "FR", "appeals-exhausted")

    # Graph slug -> upload node alias -> upload node. Each upload node is its
    # own nodegroup.
    UPLOAD_NODES = {
        GraphSlugs.ARCHAEOLOGICAL_SITE: {
            Site.RELATED_SITE_DOCUMENTS: UploadNode(
                SITE_INVENTORY, type_alias=Site.RELATED_DOCUMENT_TYPE
            ),
            Site.SITE_IMAGES: UploadNode(SITE_INVENTORY, type_alias=Site.IMAGE_TYPE),
            Site.CONTRAVENTION_DOCUMENT: UploadNode(VIOLATION_CASE),
            Site.RESTRICTED_DOCUMENT: UploadNode(
                SITE_INVENTORY, sensitivity=Sensitivity.SITE_LOCATION
            ),
        },
        GraphSlugs.SITE_VISIT: {
            Visit.RELATED_SITE_DOCUMENTS: UploadNode(
                SITE_INVENTORY, type_alias=Visit.RELATED_DOCUMENT_TYPE
            ),
            Visit.SITE_IMAGES: UploadNode(SITE_INVENTORY, type_alias=Visit.IMAGE_TYPE),
        },
    }

    # Labels from the Document Type list. Site images use the separate Image
    # Type list, which isn't mapped yet, so every site image needs review until
    # the Records Officer maps it (air photos and sonar printouts can show where
    # a site is).
    DOCUMENT_TYPES = {
        "map": Sensitivity.SITE_LOCATION,
        "map, other": Sensitivity.SITE_LOCATION,
        "map, detailed": Sensitivity.SITE_LOCATION,
        "map, midrange": Sensitivity.SITE_LOCATION,
        "stratigraphy profile": Sensitivity.SITE_LOCATION,
    }

    LOCATION_EXTENSIONS = set(
        "shp shx dbf prj cpg sbn sbx kml kmz geojson gpx gpkg gdb dwg dxf mif tab"
        " qgs qgz mxd las laz ply obj e57 xyz zip 7z rar tar gz tgz".split()
    )

    @classmethod
    def tags_for(cls, instance: File, extension: str, graph_slug: str):
        """The tags for a file being saved."""
        node_alias, doc_type = "", ""
        try:
            node_alias, doc_type = cls.node_and_document_type(instance.tile, graph_slug)
        except Exception:
            logger.exception(
                "Could not find the upload node; classifying as restricted"
            )
        tags = cls.classify(
            upload=cls.UPLOAD_NODES.get(graph_slug, {}).get(node_alias),
            doc_type=doc_type,
            extension=extension,
            resource_id=instance.tile.resourceinstance.resourceinstanceid,
        )
        cls.log(tags, graph_slug, node_alias, doc_type)
        return tags

    @classmethod
    def classify(
        cls,
        *,
        upload: UploadNode | None,
        doc_type: str,
        extension: str,
        resource_id: uuid.UUID | str,
    ):
        """The S3 tags for one upload. No upload node means an unknown one."""
        matched = cls.rule_sensitivities(upload, doc_type, extension)
        if upload is None:
            return RecordTags(
                sensitivity_class=cls.most_sensitive(
                    matched | {Sensitivity.SITE_LOCATION}
                ),
                resource_instance_id=str(resource_id),
            )
        return RecordTags(
            orcs_classification=upload.orcs.number,
            disposition_class=upload.orcs.disposition,
            retention_trigger=upload.orcs.retention_trigger,
            retention_period=upload.orcs.retention_period,
            sensitivity_class=cls.most_sensitive(
                matched or {Sensitivity.SITE_LOCATION}
            ),
            resource_instance_id=str(resource_id),
            classification_status=Status.AUTO if matched else Status.NEEDS_REVIEW,
        )

    @classmethod
    def rule_sensitivities(
        cls, upload: UploadNode | None, doc_type: str, extension: str
    ):
        """Every sensitivity the rules give this upload: a fixed one on its upload
        node in the upload table (the restricted document node), its document type
        in the document type table, and a spatial file extension. The most
        sensitive one wins; none means needs-review."""
        matched = set()
        if upload and upload.sensitivity:
            matched.add(upload.sensitivity)
        if type_sensitivity := cls.DOCUMENT_TYPES.get(doc_type.strip().lower()):
            matched.add(type_sensitivity)
        if extension.lstrip(".").lower() in cls.LOCATION_EXTENSIONS:
            matched.add(Sensitivity.SITE_LOCATION)
        return matched

    @staticmethod
    def most_sensitive(sensitivities: set[Sensitivity]):
        """The one listed first in the enum, which is ordered most sensitive first."""
        return min(sensitivities, key=list(Sensitivity).index)

    @classmethod
    def node_and_document_type(cls, tile: TileModel, graph_slug: str):
        """(upload node alias, document type) for the tile, or ("", "")."""
        uploads = cls.UPLOAD_NODES.get(graph_slug, {})
        nodes = {
            n.alias: n for n in Node.objects.filter(nodegroup_id=tile.nodegroup_id)
        }
        alias = next((a for a in uploads if a in nodes), "")
        type_alias = alias and uploads[alias].type_alias
        if not type_alias:
            return alias, ""
        return alias, ReferenceDataType().get_display_value(
            tile, nodes[type_alias], language="en"
        )

    @staticmethod
    def log(tags: RecordTags, graph_slug: str, node_alias: str, doc_type: str):
        unclassified = tags.classification_status == Status.UNCLASSIFIED
        logger.log(
            logging.WARNING if unclassified else logging.DEBUG,
            "Upload on %s %s (node %s, type %r) is %s: %s",
            graph_slug,
            tags.resource_instance_id,
            node_alias or "unknown",
            doc_type,
            tags.classification_status,
            tags.as_s3(),
        )
