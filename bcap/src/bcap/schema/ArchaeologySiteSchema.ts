import type {
    AliasedData,
    AliasedNodeData,
    AliasedTileData,
} from "@/arches_component_lab/types.ts";
import type { ReferenceSelectValue } from "@/arches_controlled_lists/datatypes/reference-select/types.ts";
import type { DateValue } from "@/arches_component_lab/datatypes/date/types.ts";
import type { StringValue } from "@/arches_component_lab/datatypes/string/types.ts";
import type { ResourceInstanceValue } from "@/arches_component_lab/datatypes/resource-instance/types.ts";
import type { FileListValue } from "@/arches_component_lab/datatypes/file-list/types.ts";

// 1) Site Boundary (only fields referenced by the template are required here)
export interface SiteBoundaryTile extends AliasedTileData {
    aliased_data: {
        // <dt>Source Notes</dt> -> currentData.aliased_data.site_boundary.aliased_data.source_notes.display_value
        source_notes?: AliasedNodeData;

        // <dt>Latest Edit Type</dt> -> ...latest_edit_type.node_value / .display_value (guarded)
        latest_edit_type?: AliasedNodeData;
    };
}

export interface AuthorityTile extends AliasedTileData {
    aliased_data: {
        authority_start_date?: AliasedNodeData;
        responsible_government?: AliasedNodeData;
        authority_end_date?: AliasedNodeData;
        legislative_act?: AliasedNodeData;
        authority_description?: AliasedNodeData;
        reference_number?: AliasedNodeData;
    };
}
export interface SiteDecisionTile extends AliasedTileData {
    aliased_data: {
        decision_date?: AliasedNodeData;
        decision_made_by?: AliasedNodeData;
        site_decision?: AliasedNodeData;
        decision_criteria?: AliasedNodeData;
        decision_description?: AliasedNodeData;
        recommendation_date?: AliasedNodeData;
        recommended_by?: AliasedNodeData;
    };
}
// --- Identification & Registration tile ---
export interface IdentificationAndRegistrationTile extends AliasedTileData {
    borden_number?: AliasedNodeData;
    registration_date?: AliasedNodeData;
    registration_status?: AliasedNodeData;
    parcel_owner_type?: AliasedNodeData;
    site_creation_date?: AliasedNodeData;
    register_type?: AliasedNodeData;
    parent_site?: AliasedNodeData;
    site_alert?: AliasedNodeData;
    authority?: AuthorityTile[];
    site_names?: AliasedTileData[]; // generic child tiles
    site_decision?: SiteDecisionTile[]; // specialized shape
}

// 3) Archaeological Data
export interface SiteTypologyTile extends AliasedTileData {
    typology_class?: AliasedNodeData;
    site_type?: AliasedNodeData;
    site_subtype?: AliasedNodeData;
    typology_descriptor?: AliasedNodeData;
    typology_remark?: AliasedNodeData;
}
export interface ArchaeologicalDataTile extends AliasedTileData {
    site_typology?: SiteTypologyTile[];
}

// 4) Ancestral Remains
export interface AncestralRemainsTile extends AliasedTileData {
    aliased_data: AliasedData;
}

/*************************************************/
// 5) Remarks & Restricted Information
/*************************************************/

export interface GeneralRemarkTile extends AliasedTileData {
    aliased_data: {
        general_remark_source?: ReferenceSelectValue;
        general_remark_date?: DateValue;
        general_remark?: StringValue;
    };
}

export interface RestrictedRemarkTile extends AliasedTileData {
    aliased_data: {
        restricted_entry_date?: DateValue;
        restricted_person?: ResourceInstanceValue;
        restricted_remark?: StringValue;
    };
}

export interface RemarksAndRestrictedInformationTile extends AliasedTileData {
    general_remark_information: GeneralRemarkTile[];

    remark_keyword?: AliasedNodeData;
    contravention_document?: AliasedNodeData;
    restricted_document?: AliasedNodeData;

    hca_contravention: AliasedTileData[];
    restricted_information_n1: RestrictedRemarkTile[];
    conviction: AliasedTileData[];
}

// 8) References & Related Documents
// The template renders: currentData?.aliased_data?.related_documents
export interface RelatedSiteDocumentsTile extends AliasedTileData {
    aliased_data: {
        related_document_description?: StringValue;
        related_document_type?: ReferenceSelectValue;
        related_site_documents?: FileListValue;
    };
}
export interface RelatedDocumentsTile extends AliasedTileData {
    related_site_documents: RelatedSiteDocumentsTile[]; // nested tile
    publication_reference: AliasedTileData[]; // [] in sample
    site_images: AliasedTileData[];
}

// --- Top-level resource schema used by the component ---

export interface ArchaeologySiteSchema extends AliasedTileData {
    aliased_data: {
        site_boundary?: SiteBoundaryTile;
        identification_and_registration?: IdentificationAndRegistrationTile;
        archaeological_data?: ArchaeologicalDataTile;
        ancestral_remains?: AncestralRemainsTile;
        remarks_and_restricted_information?: RemarksAndRestrictedInformationTile;

        // This is read in the template but wasn’t in your initial schema.
        related_documents?: RelatedDocumentsTile;

        //     // Permit future sections without breaking types
        //     [key: string]:
        //         | AliasedNodeData
        //         | AliasedNodegroupData
        //         | SiteBoundaryTile
        //         | IdentificationAndRegistrationTile
        //         | ArchaeologicalDataTile
        //         | AncestralRemainsTile
        //         | RemarksAndRestrictedInformationTile
        //         | RelatedDocumentsTile
        //         | undefined;
    };
}
