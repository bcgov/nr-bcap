// ---------- Imports ----------
import type {
    AliasedNodeData,
    AliasedTileData,
} from '@/arches_vue_components/types.ts';
import type { StringAliasedNodeData } from '@/arches_vue_components/datatypes/string/types.ts';
import type { DateAliasedNodeData } from '@/arches_vue_components/datatypes/date/types.ts';
import type { ResourceInstanceAliasedNodeData } from '@/arches_vue_components/datatypes/resource-instance/types.ts';
import type { ResourceInstanceListAliasedNodeData } from '@/arches_vue_components/datatypes/resource-instance-list/types.ts';
import type { FileListAliasedNodeData } from '@/arches_vue_components/datatypes/file-list/types.ts';

import type { NumberAliasedNodeData } from '@/arches_vue_components/datatypes/number/types.ts';
import type { BooleanAliasedNodeData } from '@/arches_vue_components/datatypes/boolean/types.ts';
import type { GeoJSONFeatureCollectionAliasedNodeData } from '@/arches_vue_components/datatypes/geojson-feature-collection/types.ts';

import type { ReferenceSelectAliasedNodeData } from '@/arches_controlled_lists/datatypes/reference-select/types.js';

// ---------- Site Visit Location: Biogeography ----------
export interface SiteVisitLocationBiogeographyTile extends AliasedTileData {
    aliased_data: {
        biogeography_description?: AliasedNodeData;
        biogeography_name?: AliasedNodeData;
        biogeography_type?: AliasedNodeData;
    };
}

// ---------- Site Visit Location ----------
export interface SiteVisitLocationTile extends AliasedTileData {
    aliased_data: {
        accuracy_remarks: StringAliasedNodeData; // string (i18n)
        latest_edit_type: ReferenceSelectAliasedNodeData; // reference
        site_visit_location: GeoJSONFeatureCollectionAliasedNodeData; // geojson-feature-collection
        location_and_access: StringAliasedNodeData; // string (i18n)
        biogeography?: SiteVisitLocationBiogeographyTile[];
    };
}

// --- ancestral_remains[] (semantic group of tiles) ---
export interface AncestralRemainsTile extends AliasedTileData {
    aliased_data: {
        ancestral_remains_type: ReferenceSelectAliasedNodeData; // reference
        multiple_burials: BooleanAliasedNodeData; // boolean
        ancestral_remains_status: ReferenceSelectAliasedNodeData; // reference
        ancestral_remains_remarks: StringAliasedNodeData; // string (i18n)
        minimum_number_of_individuals: NumberAliasedNodeData; // number
        ancestral_remains_repository: ResourceInstanceAliasedNodeData;
    };
}

// --- identification (with children new_site_names[] & temporary_number) ---
export interface NewSiteNameTile extends AliasedTileData {
    aliased_data: {
        name: StringAliasedNodeData; // string (i18n)
        assigned_or_reported_by: ResourceInstanceAliasedNodeData;
        name_type: ReferenceSelectAliasedNodeData; // reference
        name_remarks: StringAliasedNodeData; // string (i18n)
        assigned_or_reported_date: DateAliasedNodeData; // date
    };
}

export interface TemporaryNumberTile extends AliasedTileData {
    aliased_data: {
        temporary_number_assigned_by: ResourceInstanceAliasedNodeData;
        temporary_number: StringAliasedNodeData; // string (i18n)
        temporary_number_assigned_date: DateAliasedNodeData; // date
    };
}

export interface IdentificationTile {
    aliased_data: {
        new_site_names: NewSiteNameTile[]; // semantic group
        temporary_number: TemporaryNumberTile;
    };
}

export interface TeamMemberTile extends AliasedTileData {
    aliased_data: {
        team_member: ResourceInstanceAliasedNodeData;
        member_roles: ReferenceSelectAliasedNodeData; // reference-list
        was_on_site: BooleanAliasedNodeData; // boolean
    };
}

export interface SiteVisitTeamTile extends AliasedTileData {
    aliased_data: {
        team_member: TeamMemberTile[]; // semantic subgroup
    };
}

export interface SiteVisitDetailsTile extends AliasedTileData {
    aliased_data: {
        site_form_authors: ResourceInstanceListAliasedNodeData; // resource-instance-list
        site_visit_type: ReferenceSelectAliasedNodeData; // reference
        first_date_of_site_visit: DateAliasedNodeData; // date (nullable in some payloads)
        last_date_of_site_visit: DateAliasedNodeData; // date
        project_description: StringAliasedNodeData; // string (i18n)
        archaeological_site: ResourceInstanceAliasedNodeData;
        associated_permit: ResourceInstanceAliasedNodeData;
        affiliation: ResourceInstanceAliasedNodeData;
        is_site_visit_permitted?: BooleanAliasedNodeData;
        site_visit_team: SiteVisitTeamTile; // semantic subgroup (child tile)
    };
}

// --- archaeological_data (multiple semantic groups) ---
export interface StratigraphyTile extends AliasedTileData {
    aliased_data: {
        stratigraphy: StringAliasedNodeData; // string (i18n)
    };
}

export interface ArchaeologicalCultureTile extends AliasedTileData {
    aliased_data: {
        culture_remarks: StringAliasedNodeData; // string (i18n)
        archaeological_culture: ReferenceSelectAliasedNodeData; // reference
    };
}

export interface SiteDisturbanceTile extends AliasedTileData {
    aliased_data: {
        disturbance_period: ReferenceSelectAliasedNodeData; // reference
        disturbance_cause: ReferenceSelectAliasedNodeData; // reference
        disturbance_remarks: StringAliasedNodeData; // string (i18n)
    };
}

export interface CulturalMaterialTile extends AliasedTileData {
    aliased_data: {
        cultural_material_type: ReferenceSelectAliasedNodeData; // reference
        cultural_material_status: ReferenceSelectAliasedNodeData; // reference
        cultural_material_details: StringAliasedNodeData; // string (i18n)
        number_of_artifacts: NumberAliasedNodeData; // number
        repository: ResourceInstanceAliasedNodeData;
    };
}

export interface ArchaeologicalFeatureTile extends AliasedTileData {
    aliased_data: {
        feature_count: NumberAliasedNodeData; // number
        archaeological_feature: ReferenceSelectAliasedNodeData; // reference (nullable)
        feature_remarks: StringAliasedNodeData; // string (i18n)
    };
}

export interface ChronologyTile extends AliasedTileData {
    aliased_data: {
        end_year_calendar: ReferenceSelectAliasedNodeData; // reference
        start_year_calendar: ReferenceSelectAliasedNodeData; // reference
        end_year_qualifier: ReferenceSelectAliasedNodeData; // reference
        determination_method: ReferenceSelectAliasedNodeData; // reference
        start_year: DateAliasedNodeData; // date
        information_source: StringAliasedNodeData; // string (i18n)
        end_year: DateAliasedNodeData; // date
        chronology_remarks: StringAliasedNodeData; // string (i18n)
        start_year_qualifier: ReferenceSelectAliasedNodeData; // reference
    };
}

export interface ArchaeologicalDataTile extends AliasedTileData {
    aliased_data: {
        stratigraphy: StratigraphyTile[];
        archaeological_culture: ArchaeologicalCultureTile[];
        site_disturbance: SiteDisturbanceTile[];
        cultural_material: CulturalMaterialTile[];
        archaeological_feature: ArchaeologicalFeatureTile[];
        chronology: ChronologyTile[];
    };
}

// --- remarks_and_recommendations ---
export interface RecommendationTile extends AliasedTileData {
    aliased_data: {
        recorders_recommendation: StringAliasedNodeData; // string (i18n)
    };
}

export interface ArchaeologyBranchRecommendationTile extends AliasedTileData {
    aliased_data: {
        archaeology_branch_recommendation: StringAliasedNodeData; // string (i18n)
    };
}

export interface GeneralRemarkTile extends AliasedTileData {
    aliased_data: {
        remark_source: ReferenceSelectAliasedNodeData; // reference
        remark_date: DateAliasedNodeData; // date
        remark: StringAliasedNodeData; // string (i18n)
    };
}

export interface RemarksAndRecommendationsTile extends AliasedTileData {
    aliased_data: {
        recommendation: RecommendationTile[]; // semantic
        archaeology_branch_recommendation: ArchaeologyBranchRecommendationTile[];
        general_remark: GeneralRemarkTile[]; // semantic
    };
}

// --- references_and_documents ---
export interface ReferencesTile extends AliasedTileData {
    aliased_data: {
        reference_type: ReferenceSelectAliasedNodeData;
        reference_title: StringAliasedNodeData;
        reference_year: StringAliasedNodeData;
        reference_authors: StringAliasedNodeData;
        reference_remarks: StringAliasedNodeData;
    };
}

export interface RelatedDocumentsTile extends AliasedTileData {
    aliased_data: {
        related_document_type: ReferenceSelectAliasedNodeData;
        related_document_description: StringAliasedNodeData;
        related_site_documents: ResourceInstanceAliasedNodeData;
    };
}

export interface PhotosTile extends AliasedTileData {
    aliased_data: {
        photo_title: StringAliasedNodeData;
        photo_description: StringAliasedNodeData;
        photographer: ResourceInstanceAliasedNodeData;
        photo_date: DateAliasedNodeData;
    };
}

export interface ReferencesAndDocumentsTile extends AliasedTileData {
    aliased_data: {
        references: ReferencesTile[];
        related_documents: RelatedDocumentsTile[];
        photos: PhotosTile[];
    };
}

export interface SiteVisitPublicationReferenceTile extends AliasedTileData {
    aliased_data: {
        reference_authors?: AliasedNodeData;
        reference_file?: AliasedNodeData;
        reference_remarks?: AliasedNodeData;
        reference_title?: AliasedNodeData;
        reference_type?: AliasedNodeData;
        reference_year?: AliasedNodeData;
    };
}

export interface SiteVisitRelatedSiteDocumentsTile extends AliasedTileData {
    aliased_data: {
        related_document_description?: AliasedNodeData;
        related_document_type?: AliasedNodeData;
        related_site_documents?: AliasedNodeData;
    };
}

export interface SiteVisitSiteImagesTile extends AliasedTileData {
    aliased_data: {
        copyright?: AliasedNodeData;
        image_date?: AliasedNodeData;
        image_description?: AliasedNodeData;
        image_features?: AliasedNodeData;
        image_type?: AliasedNodeData;
        image_view?: AliasedNodeData;
        photographer?: AliasedNodeData;
        primary_image?: AliasedNodeData;
        site_images?: FileListAliasedNodeData;
    };
}

export interface SiteVisitRelatedDocumentsTile extends AliasedTileData {
    publication_reference?: SiteVisitPublicationReferenceTile[];
    related_site_documents?:
        SiteVisitRelatedSiteDocumentsTile[] | SiteVisitRelatedSiteDocumentsTile;
    site_images?: SiteVisitSiteImagesTile[];
}

// ====================================================================
// Root objects
// ====================================================================
export interface SiteVisitAliasedDataRoot {
    site_visit_location: SiteVisitLocationTile;
    ancestral_remains: AncestralRemainsTile[];
    identification: IdentificationTile;
    site_visit_details: SiteVisitDetailsTile;
    archaeological_data: ArchaeologicalDataTile;
    remarks_and_recommendations: RemarksAndRecommendationsTile;
    references_and_documents: ReferencesAndDocumentsTile;
    related_documents?: SiteVisitRelatedDocumentsTile;
}

export interface SiteVisitSchema {
    resourceinstanceid: string;
    aliased_data: SiteVisitAliasedDataRoot;

    // extra metadata present in payload
    graph_has_different_publication: boolean;
    name: string;
    descriptors: Record<
        string,
        { name: string; map_popup: string; description: string }
    >;
    legacyid: string;
    createdtime: string; // ISO timestamp
    graph: string;
    graph_publication: string;
    resource_instance_lifecycle_state: string;
    principaluser: string | null;
}

export interface SiteVisitResponse {
    count: number;
    next: string | null;
    previous: string | null;
    results: SiteVisitSchema[];
}
