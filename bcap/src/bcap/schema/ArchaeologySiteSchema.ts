import type {
    AliasedData,
    AliasedNodeData,
    AliasedTileData,
} from "@/arches_component_lab/types.ts";

// 1) Site Boundary (only fields referenced by the template are required here)
export interface SiteBoundaryTile extends AliasedTileData {
    aliased_data: {
        // <dt>Source Notes</dt> -> currentData.aliased_data.site_boundary.aliased_data.source_notes.display_value
        source_notes?: AliasedNodeData;

        // <dt>Latest Edit Type</dt> -> ...latest_edit_type.node_value / .display_value (guarded)
        latest_edit_type?: AliasedNodeData;
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
    authority?: AliasedNodeData;
    site_names?: AliasedTileData[]; // generic child tiles
    site_decision?: SiteDecisionTile[]; // specialized shape
}

// 3) Archaeological Data
export interface ArchaeologicalDataTile extends AliasedTileData {
    aliased_data: AliasedData;
}

// 4) Ancestral Remains
export interface AncestralRemainsTile extends AliasedTileData {
    aliased_data: AliasedData;
}

// 5) Remarks & Restricted Information
export interface RemarksAndRestrictedInformationTile extends AliasedTileData {
    aliased_data: AliasedData;
}

// 6) References & Related Documents
// The template renders: currentData?.aliased_data?.related_documents
export interface RelatedDocumentsTile extends AliasedTileData {
    aliased_data: AliasedData;
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
