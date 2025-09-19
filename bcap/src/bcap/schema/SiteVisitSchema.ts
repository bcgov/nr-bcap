import type {
    AliasedNodeData,
    AliasedTileData,
} from "@/arches_component_lab/types.ts";

import type { StringValue } from "@/arches_component_lab/datatypes/string/types.ts";
import type { DateValue } from "@/arches_component_lab/datatypes/date/types.ts";
import type { ResourceInstanceValue } from "@/arches_component_lab/datatypes/resource-instance/types.ts";
import type { ResourceInstanceListValue } from "@/arches_component_lab/datatypes/resource-instance-list/types.ts";

import type { ReferenceSelectValue } from "@/arches_controlled_lists/datatypes/reference-select/types.js";

import type {
    NumberValue,
    BooleanValue,
    GeoJSONFeatureCollectionValue,
    NullableReferenceSelectValue,
} from "@/bcap/types.ts";

export interface SiteVisitLocationTile extends AliasedTileData {
    aliased_data: {
        source_notes: StringValue;
        accuracy_remarks: StringValue;
        latest_edit_type: ReferenceSelectValue;
        site_visit_location: GeoJSONFeatureCollectionValue;
        location_and_access: StringValue;
    };
}

export interface AncestralRemainsTile extends AliasedTileData {
    aliased_data: {
        ancestral_remains_type: ReferenceSelectValue;
        multiple_burials: BooleanValue;
        ancestral_remains_status: ReferenceSelectValue;
        ancestral_remains_remarks: StringValue;
        minimum_number_of_individuals: NumberValue;
        ancestral_remains_repository: ResourceInstanceValue;
    };
}

export interface NewSiteNameTile extends AliasedTileData {
    aliased_data: {
        name: StringValue;
        assigned_or_reported_by: ResourceInstanceValue;
        name_type: ReferenceSelectValue;
        name_remarks: StringValue;
        assigned_or_reported_date: DateValue;
    };
}

export interface TemporaryNumberTile extends AliasedTileData {
    aliased_data: {
        temporary_number_assigned_by: ResourceInstanceValue;
        temporary_number: StringValue;
        temporary_number_assigned_date: DateValue;
    };
}

export interface IdentificationTile {
    aliased_data: {
        new_site_names: NewSiteNameTile[];
        temporary_number: TemporaryNumberTile;
    };
}

export interface TeamMemberTile extends AliasedTileData {
    aliased_data: {
        team_member: ResourceInstanceValue;
        member_roles: ReferenceSelectValue;
        was_on_site: BooleanValue;
    };
}

export interface SiteVisitTeamTile extends AliasedTileData {
    aliased_data: {
        team_member: TeamMemberTile[];
    };
}

export interface SiteVisitDetailsTile extends AliasedTileData {
    aliased_data: {
        site_form_authors: ResourceInstanceListValue;
        site_visit_type: ReferenceSelectValue;
        first_date_of_site_visit: DateValue;
        last_date_of_site_visit: DateValue;
        project_description: StringValue;
        archaeological_site: ResourceInstanceValue;
        associated_permit: ResourceInstanceValue;
        affiliation: ResourceInstanceValue;
        site_visit_team_n1: SiteVisitTeamTile;
    };
}

export interface StratigraphyTile extends AliasedTileData {
    aliased_data: {
        stratigraphy: StringValue;
    };
}

export interface ArchaeologicalCultureTile extends AliasedTileData {
    aliased_data: {
        culture_remarks: StringValue;
        archaeological_culture: ReferenceSelectValue;
    };
}

export interface SiteDisturbanceTile extends AliasedTileData {
    aliased_data: {
        disturbance_period: ReferenceSelectValue;
        disturbance_cause: ReferenceSelectValue;
        disturbance_remarks: StringValue;
    };
}

export interface CulturalMaterialTile extends AliasedTileData {
    aliased_data: {
        cultural_material_type: ReferenceSelectValue;
        cultural_material_status: ReferenceSelectValue;
        cultural_material_details: StringValue;
        number_of_artifacts: NumberValue;
        repository: ResourceInstanceValue;
    };
}

export interface ArchaeologicalFeatureTile extends AliasedTileData {
    aliased_data: {
        feature_count: NumberValue;
        archaeological_feature: NullableReferenceSelectValue;
        feature_remarks: StringValue;
    };
}

export interface ChronologyTile extends AliasedTileData {
    aliased_data: {
        end_year_calendar: ReferenceSelectValue;
        start_year_calendar: ReferenceSelectValue;
        end_year_qualifier: ReferenceSelectValue;
        determination_method: ReferenceSelectValue;
        start_year: DateValue;
        information_source: StringValue;
        end_year: DateValue;
        chronology_remarks: StringValue;
        start_year_qualifier: ReferenceSelectValue;
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

export interface RecommendationTile extends AliasedTileData {
    aliased_data: {
        recorders_recommendation: StringValue;
    };
}

export interface GeneralRemarkTile extends AliasedTileData {
    aliased_data: {
        remark_source: ReferenceSelectValue;
        remark_date: DateValue;
        remark: StringValue;
    };
}

export interface ReferencesTile extends AliasedTileData {
    aliased_data: {
        reference_type: ReferenceSelectValue;
        reference_title: StringValue;
        publication_year: DateValue;
        reference_authors: StringValue;
        reference_remarks: StringValue;
    };
}

export interface RelatedDocumentsTile extends AliasedTileData {
    aliased_data: {
        document_type: ReferenceSelectValue;
        document_title: StringValue;
        document_description: StringValue;
    };
}

export interface PhotosTile extends AliasedTileData {
    aliased_data: {
        photo_title: StringValue;
        photo_description: StringValue;
        photographer: ResourceInstanceValue;
        photo_date: DateValue;
    };
}

export interface ReferencesAndDocumentsTile extends AliasedTileData {
    aliased_data: {
        references: ReferencesTile[];
        related_documents: RelatedDocumentsTile[];
        photos: PhotosTile[];
    };
}

export interface RemarksAndRecommendationsTile extends AliasedTileData {
    aliased_data: {
        recommendation: RecommendationTile[];
        general_remark: GeneralRemarkTile[];
    };
}

export interface SiteVisitAliasedDataRoot {
    site_visit_location: SiteVisitLocationTile;
    ancestral_remains: AncestralRemainsTile[];
    identification: IdentificationTile;
    site_visit_details: SiteVisitDetailsTile;
    archaeological_data: ArchaeologicalDataTile;
    remarks_and_recommendations: RemarksAndRecommendationsTile;
    references_and_documents: ReferencesAndDocumentsTile;
}

export interface SiteVisitSchema {
    resourceinstanceid: string;
    aliased_data: SiteVisitAliasedDataRoot;

    graph_has_different_publication: boolean;
    name: string;
    descriptors: Record<
        string,
        { name: string; map_popup: string; description: string }
    >;
    legacyid: string;
    createdtime: string;
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
