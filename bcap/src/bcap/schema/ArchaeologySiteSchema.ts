import type {
    AliasedNodeData,
    AliasedTileData,
} from '@/arches_component_lab/types.ts';
import type { FileListValue } from '@/arches_component_lab/datatypes/file-list/types.ts';
import type { ArchesResourceInstanceData } from '@/bcgov_arches_common/types.ts';
import type { AliasedGeojsonFeatureCollectionNode } from '@/bcgov_arches_common/datatypes/geojson-feature-collection/types.ts';
import type { ReferenceSelectValue } from '@/arches_controlled_lists/datatypes/reference-select/types.ts';
import type { DateValue } from '@/arches_component_lab/datatypes/date/types.ts';
import type { StringValue } from '@/arches_component_lab/datatypes/string/types.ts';

export interface SpatialAccuracyEntry extends AliasedTileData {
    aliased_data: {
        edit_type?: AliasedNodeData;
        accuracy_remarks?: AliasedNodeData;
        edited_on?: AliasedNodeData;
        edited_by?: AliasedNodeData;
    };
}

export interface SiteBoundaryTile extends AliasedTileData {
    aliased_data: {
        site_boundary?: AliasedGeojsonFeatureCollectionNode;
        latest_edit_type?: AliasedNodeData;
        source_notes?: AliasedNodeData;
        accuracy_remarks?: AliasedNodeData;
        spatial_accuracy_history?: SpatialAccuracyEntry[];
        site_boundary_description?: AliasedNodeData;
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
        decision_registration_status?: AliasedNodeData;
        recommendation_date?: AliasedNodeData;
        recommended_by?: AliasedNodeData;
    };
}

export interface CurrentAlertTile extends AliasedTileData {
    aliased_data: {
        alert_subject?: AliasedNodeData;
        alert_details?: AliasedNodeData;
        alert_branch_contact?: AliasedNodeData;
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
    parcel_owner_type?: AliasedNodeData;
    borden_number_issuance_date?: AliasedNodeData;
    register_type?: AliasedNodeData;
    parent_site?: AliasedNodeData;
    child_sites?: AliasedNodeData[];
    site_alert?: CurrentAlertTile[] | CurrentAlertTile;
    authority?: AuthorityTile[];
    site_names?: SiteNamesTile[];
    site_decision?: SiteDecisionTile[];
}

// 3) Archaeological Data
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

// 4) Ancestral Remains
export interface RestrictedAncestralRemainsRemarkTile extends AliasedTileData {
    aliased_data: {
        restricted_ancestral_remains_remark?: AliasedNodeData;
    };
}

export interface AncestralRemainsTile extends AliasedTileData {
    aliased_data: {
        restricted_ancestral_remains_remark?:
            | RestrictedAncestralRemainsRemarkTile[]
            | RestrictedAncestralRemainsRemarkTile;
    };
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

export interface TenureAndReservesTile extends AliasedTileData {
    aliased_data: {
        tenure_type?: AliasedNodeData;
        tenure_description?: AliasedNodeData;
    };
}

export interface TenureRemarksTile extends AliasedTileData {
    aliased_data: {
        tenure_remarks?: AliasedNodeData;
        entered_on?: AliasedNodeData;
        entered_by?: AliasedNodeData;
    };
}

export interface AddressRemarksTile extends AliasedTileData {
    aliased_data: {
        address_and_legal_description_remarks?: AliasedNodeData;
        entered_on?: AliasedNodeData;
        entered_by?: AliasedNodeData;
    };
}

export interface CoordinatesTile extends AliasedTileData {
    aliased_data: {
        utm_zone?: AliasedNodeData;
        utm_easting?: AliasedNodeData;
        utm_northing?: AliasedNodeData;
        latitude?: AliasedNodeData;
        longitude?: AliasedNodeData;
    };
}

export interface SiteLocationTile extends AliasedTileData {
    coordinates?: CoordinatesTile;
    tenure_and_reserves?: TenureAndReservesTile[];
    tenure_remarks?: TenureRemarksTile[];
    bc_property_address?: BcPropertyAddressTile[];
    address_remarks?: AddressRemarksTile;
    elevation?: ElevationTile;
    biogeography?: SiteLocationBiogeographyTile[];
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
        restricted_remark?: StringValue;
    };
}

export interface ContraventionDocumentTile extends AliasedTileData {
    aliased_data: {
        contravention_document?: AliasedNodeData;
    };
}

export interface RestrictedDocumentTile extends AliasedTileData {
    aliased_data: {
        restricted_document?: AliasedNodeData;
    };
}

export interface RemarksAndRestrictedInformationTile extends AliasedTileData {
    general_remark_information: GeneralRemarkTile[];
    remark_keyword?: AliasedNodeData;
    contravention_document?: ContraventionDocumentTile[];
    restricted_document?: RestrictedDocumentTile[];
    hca_contravention: AliasedTileData[];
    restricted_information: RestrictedRemarkTile[];
    conviction: AliasedTileData[];
}

export interface PublicationReferenceTile extends AliasedTileData {
    aliased_data: {
        reference_type?: AliasedNodeData;
        reference_title?: AliasedNodeData;
        reference_year?: AliasedNodeData;
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
        site_images?: FileListValue;
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

type ArchaeologySiteAliasedData = {
    site_boundary?: SiteBoundaryTile;
    identification_and_registration?: IdentificationAndRegistrationTile;
    archaeological_data?: ArchaeologicalDataTile;
    heritage_site_location?: SiteLocationTile[];
    site_location?: SiteLocationTile;
    ancestral_remains?: AncestralRemainsTile;
    remarks_and_restricted_information?: RemarksAndRestrictedInformationTile;
    related_documents?: RelatedDocumentsTile;
};

export interface ArchaeologySiteSchema extends ArchesResourceInstanceData<ArchaeologySiteAliasedData> {
    aliased_data: ArchaeologySiteAliasedData;
}
