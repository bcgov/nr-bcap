// ---------- Imports ----------
import type {
    AliasedNodeData,
    AliasedTileData,
} from "@/arches_component_lab/types.ts";

import type { StringValue } from "@/arches_component_lab/datatypes/string/types.ts";
import type { DateValue } from "@/arches_component_lab/datatypes/date/types.ts";
import type { ResourceInstanceValue } from "@/arches_component_lab/datatypes/resource-instance/types.ts";
import type { ResourceInstanceListValue } from "@/arches_component_lab/datatypes/resource-instance-list/types.ts";

// Controlled list “reference / reference-list”
import type {
    ReferenceSelectValue,
    ReferenceSelectNodeValue,
    ReferenceSelectDetails,
} from "@/arches_controlled_lists/datatypes/reference-select/types.js";

// ---------- Small local helpers ----------
export interface NumberValue extends AliasedNodeData {
    display_value: string;
    node_value: number | null;
    details: never[];
}

export interface BooleanValue extends AliasedNodeData {
    display_value: string;
    node_value: boolean | null;
    details: never[];
}

export interface GeoJSONFeatureCollectionValue extends AliasedNodeData {
    display_value: string;
    node_value: {
        type: "FeatureCollection";
        features: unknown[]; // supply a stricter Feature type if you have one
    } | null;
    details: never[];
}

// Some reference nodes can be null; keep your ReferenceSelectValue shape
export type NullableReferenceSelectValue =
    | ReferenceSelectValue
    | (Omit<ReferenceSelectValue, "node_value" | "details"> & {
          node_value: ReferenceSelectNodeValue[] | null;
          details: ReferenceSelectDetails[] | [];
      });

// ====================================================================
// Site Visit tiles (datatype-specific leaf nodes)
// ====================================================================

// --- site_visit_location ---
export interface SiteVisitLocationTile extends AliasedTileData {
    aliased_data: {
        source_notes: StringValue; // string (i18n)
        accuracy_remarks: StringValue; // string (i18n)
        latest_edit_type: ReferenceSelectValue; // reference
        site_visit_location: GeoJSONFeatureCollectionValue; // geojson-feature-collection
        location_and_access: StringValue; // string (i18n)
    };
}

// --- ancestral_remains[] (semantic group of tiles) ---
export interface AncestralRemainsTile extends AliasedTileData {
    aliased_data: {
        ancestral_remains_type: ReferenceSelectValue; // reference
        multiple_burials: BooleanValue; // boolean
        ancestral_remains_status: ReferenceSelectValue; // reference
        ancestral_remains_remarks: StringValue; // string (i18n)
        minimum_number_of_individuals: NumberValue; // number
        ancestral_remains_repository: ResourceInstanceValue;
    };
}

// --- identification (with children new_site_names[] & temporary_number) ---
export interface NewSiteNameTile extends AliasedTileData {
    aliased_data: {
        name: StringValue; // string (i18n)
        assigned_or_reported_by: ResourceInstanceValue;
        name_type: ReferenceSelectValue; // reference
        name_remarks: StringValue; // string (i18n)
        assigned_or_reported_date: DateValue; // date
    };
}

export interface TemporaryNumberTile extends AliasedTileData {
    aliased_data: {
        temporary_number_assigned_by: ResourceInstanceValue;
        temporary_number: StringValue; // string (i18n)
        temporary_number_assigned_date: DateValue; // date
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
        team_member: ResourceInstanceValue;
        member_roles: ReferenceSelectValue; // reference-list
        was_on_site: BooleanValue; // boolean
    };
}

export interface SiteVisitTeamTile extends AliasedTileData {
    aliased_data: {
        team_member: TeamMemberTile[]; // semantic subgroup
    };
}

export interface SiteVisitDetailsTile extends AliasedTileData {
    aliased_data: {
        site_form_authors: ResourceInstanceListValue; // resource-instance-list
        site_visit_type: ReferenceSelectValue; // reference
        first_date_of_site_visit: DateValue; // date (nullable in some payloads)
        last_date_of_site_visit: DateValue; // date
        project_description: StringValue; // string (i18n)
        archaeological_site: ResourceInstanceValue;
        associated_permit: ResourceInstanceValue;
        affiliation: ResourceInstanceValue;
        site_visit_team_n1: SiteVisitTeamTile; // semantic subgroup (child tile)
    };
}

// --- archaeological_data (multiple semantic groups) ---
export interface StratigraphyTile extends AliasedTileData {
    aliased_data: {
        stratigraphy: StringValue; // string (i18n)
    };
}

export interface ArchaeologicalCultureTile extends AliasedTileData {
    aliased_data: {
        culture_remarks: StringValue; // string (i18n)
        archaeological_culture: ReferenceSelectValue; // reference
    };
}

export interface SiteDisturbanceTile extends AliasedTileData {
    aliased_data: {
        disturbance_period: ReferenceSelectValue; // reference
        disturbance_cause: ReferenceSelectValue; // reference
        disturbance_remarks: StringValue; // string (i18n)
    };
}

export interface CulturalMaterialTile extends AliasedTileData {
    aliased_data: {
        cultural_material_type: ReferenceSelectValue; // reference
        cultural_material_status: ReferenceSelectValue; // reference
        cultural_material_details: StringValue; // string (i18n)
        number_of_artifacts: NumberValue; // number
        repository: ResourceInstanceValue;
    };
}

export interface ArchaeologicalFeatureTile extends AliasedTileData {
    aliased_data: {
        feature_count: NumberValue; // number
        archaeological_feature: NullableReferenceSelectValue; // reference (nullable)
        feature_remarks: StringValue; // string (i18n)
    };
}

export interface ChronologyTile extends AliasedTileData {
    aliased_data: {
        end_year_calendar: ReferenceSelectValue; // reference
        start_year_calendar: ReferenceSelectValue; // reference
        end_year_qualifier: ReferenceSelectValue; // reference
        determination_method: ReferenceSelectValue; // reference
        start_year: DateValue; // date
        information_source: StringValue; // string (i18n)
        end_year: DateValue; // date
        chronology_remarks: StringValue; // string (i18n)
        start_year_qualifier: ReferenceSelectValue; // reference
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
        recorders_recommendation: StringValue; // string (i18n)
    };
}

export interface GeneralRemarkTile extends AliasedTileData {
    aliased_data: {
        remark_source: ReferenceSelectValue; // reference
        remark_date: DateValue; // date
        remark: StringValue; // string (i18n)
    };
}

export interface RemarksAndRecommendationsTile extends AliasedTileData {
    aliased_data: {
        recommendation: RecommendationTile[]; // semantic
        general_remark: GeneralRemarkTile[]; // semantic
    };
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
