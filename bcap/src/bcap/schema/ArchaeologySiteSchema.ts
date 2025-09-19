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

export interface SiteBoundaryTile extends AliasedTileData {
    aliased_data: {
        site_boundary?: AliasedNodeData;
        latest_edit_type?: AliasedNodeData;
        source_notes?: AliasedNodeData;
        accuracy_remarks?: AliasedNodeData;
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

export interface CurrentAlertTile extends AliasedTileData {
    aliased_data: {
        alert_subject?: AliasedNodeData;
        alert_details?: AliasedNodeData;
        branch_contact?: AliasedNodeData;
        entered_on?: AliasedNodeData;
        entered_by?: AliasedNodeData;
    };
}

export interface SiteNamesTile extends AliasedTileData {
    aliased_data: {
        site_name?: AliasedNodeData;
        site_name_type?: AliasedNodeData;
        site_name_remarks?: AliasedNodeData;
        date_assigned_or_reported?: AliasedNodeData;
        assigned_or_reported_by?: AliasedNodeData;
        entered_on?: AliasedNodeData;
        entered_by?: AliasedNodeData;
    };
}

export interface IdentificationAndRegistrationTile extends AliasedTileData {
    borden_number?: AliasedNodeData;
    registration_date?: AliasedNodeData;
    registration_status?: AliasedNodeData;
    parcel_owner_type?: AliasedNodeData;
    site_creation_date?: AliasedNodeData;
    register_type?: AliasedNodeData;
    parent_site?: AliasedNodeData;
    child_sites?: AliasedNodeData[];
    site_alert?: CurrentAlertTile[] | CurrentAlertTile | AliasedNodeData;
    authority?: AuthorityTile[];
    site_names?: SiteNamesTile[];
    site_decision?: SiteDecisionTile[];
}

export interface SiteTypologyTile extends AliasedTileData {
    typology_class?: AliasedNodeData;
    site_type?: AliasedNodeData;
    site_subtype?: AliasedNodeData;
    typology_descriptor?: AliasedNodeData;
}

export interface SiteTypologyRemarksTile extends AliasedTileData {
    aliased_data: {
        site_typology_remarks?: AliasedNodeData;
        entered_on?: AliasedNodeData;
        entered_by?: AliasedNodeData;
    };
}

export interface ArchaeologicalDataTile extends AliasedTileData {
    site_typology?: SiteTypologyTile[];
    site_typology_remarks?: AliasedTileData[];
}

export interface AncestralRemainsTile extends AliasedTileData {
    aliased_data: AliasedData;
}

export interface BcPropertyLegalDescriptionTile extends AliasedTileData {
    aliased_data: {
        legal_description?: AliasedNodeData;
        legal_address_remarks?: AliasedNodeData;
        pid?: AliasedNodeData;
        pin?: AliasedNodeData;
    };
}

export interface BcPropertyAddressTile extends AliasedTileData {
    aliased_data: {
        street_number?: AliasedNodeData;
        postal_code?: AliasedNodeData;
        street_name?: AliasedNodeData;
        city?: AliasedNodeData;
        address_remarks?: AliasedNodeData;
        bc_property_legal_description?: BcPropertyLegalDescriptionTile[];
    };
}

export interface ElevationCommentsTile extends AliasedTileData {
    aliased_data: {
        elevation_comments?: AliasedNodeData;
    };
}

export interface ElevationTile extends AliasedTileData {
    aliased_data: {
        gis_lower_elevation?: AliasedNodeData;
        gis_upper_elevation?: AliasedNodeData;
        elevation_comments?: ElevationCommentsTile[];
    };
}

export interface SiteLocationBiogeographyTile extends AliasedTileData {
    aliased_data: {
        biogeography_description?: AliasedNodeData;
        biogeography_name?: AliasedNodeData;
        biogeography_type?: AliasedNodeData;
    };
}

export interface SiteLocationTile extends AliasedTileData {
    bc_property_address?: BcPropertyAddressTile[];
    elevation?: ElevationTile;
    biogeography?: SiteLocationBiogeographyTile[];
    site_tenure?: any;
}

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

export interface PublicationReferenceTile extends AliasedTileData {
    aliased_data: {
        reference_type?: AliasedNodeData;
        reference_title?: AliasedNodeData;
        publication_year?: AliasedNodeData;
        reference_authors?: AliasedNodeData;
        reference_remarks?: AliasedNodeData;
    };
}

export interface RelatedSiteDocumentsTile extends AliasedTileData {
    aliased_data: {
        related_document_description?: AliasedNodeData;
        related_document_type?: AliasedNodeData;
        related_site_documents?: AliasedNodeData;
    };
}

export interface SiteImagesTile extends AliasedTileData {
    aliased_data: {
        image_type?: AliasedNodeData;
        repository?: AliasedNodeData;
        photographer?: AliasedNodeData;
        image_description?: AliasedNodeData;
        image_caption?: AliasedNodeData;
        image_date?: AliasedNodeData;
        modified_on?: AliasedNodeData;
        modified_by?: AliasedNodeData;
    };
}

export interface OtherMapsTile extends AliasedTileData {
    aliased_data: {
        map_name?: AliasedNodeData;
        map_scale?: AliasedNodeData;
        modified_on?: AliasedNodeData;
        modified_by?: AliasedNodeData;
    };
}

export interface RelatedDocumentsTile extends AliasedTileData {
    publication_reference?: PublicationReferenceTile[];
    related_site_documents?:
        | RelatedSiteDocumentsTile[]
        | RelatedSiteDocumentsTile;
    site_images?: SiteImagesTile[];
    other_maps?: OtherMapsTile[];
}

export interface ArchaeologySiteSchema extends AliasedTileData {
    aliased_data: {
        site_boundary?: SiteBoundaryTile;
        identification_and_registration?: IdentificationAndRegistrationTile;
        archaeological_data?: ArchaeologicalDataTile;
        heritage_site_location?: SiteLocationTile[];
        site_location?: SiteLocationTile;
        ancestral_remains?: AncestralRemainsTile;
        remarks_and_restricted_information?: RemarksAndRestrictedInformationTile;
        related_documents?: RelatedDocumentsTile;
    };
}
