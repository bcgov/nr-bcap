import type {
    AliasedNodeData,
    AliasedTileData,
} from "@/arches_component_lab/types.ts";
import type { StringValue } from "@/arches_component_lab/datatypes/string/types.ts";
import type { NonLocalizedTextValue } from "@/arches_component_lab/datatypes/non-localized-text/types.ts";
import type { DateValue } from "@/arches_component_lab/datatypes/date/types.ts";
import type { ResourceInstanceListValue } from "@/arches_component_lab/datatypes/resource-instance-list/types.ts";
import type {
    ReferenceSelectValue,
} from "@/arches_controlled_lists/datatypes/reference-select/types.js";
import type {
    NumberValue,
    BooleanValue,
    NullableReferenceSelectValue,
} from "@/bcap/types.ts";

export interface BiogeographyTile extends AliasedTileData {
    aliased_data: {
        biogeography_type: NonLocalizedTextValue;
        biogeography_entered_by: NonLocalizedTextValue;
        biogeography_entered_date: DateValue;
        biogeography_name: StringValue;
        biogeography_description: StringValue;
    };
}

export interface UnreviewedAdifRecordTile extends AliasedTileData {
    aliased_data: {
        unreviewed_adif_record: BooleanValue;
        site_entered_by: NonLocalizedTextValue;
        site_entry_date: DateValue;
    };
}

export interface ArchaeologicalSiteTile extends AliasedTileData {
    aliased_data: {
        archaeological_site: ResourceInstanceListValue;
    };
}

export interface HriaJurisdictionAndTenureTile extends AliasedTileData {
    aliased_data: {
        site_jurisdiction: StringValue;
        tenure_identifier: StringValue;
        jurisdiction_entered_by: StringValue;
        jurisdiction_entered_date: DateValue;
        tenure_type: StringValue;
        tenure_remarks: StringValue;
    };
}

export interface ChronologyTile extends AliasedTileData {
    aliased_data: {
        end_year_qualifier: NullableReferenceSelectValue;
        end_year_calendar: ReferenceSelectValue;
        determination_method: ReferenceSelectValue;
        start_year: DateValue;
        end_year: DateValue;
        start_year_calendar: ReferenceSelectValue;
        start_year_qualifier: NullableReferenceSelectValue;
        information_source: StringValue;
        chronology_remarks: StringValue;
        rcd_lab_code: NonLocalizedTextValue;
        rcd_unadjusted: NonLocalizedTextValue;
        rcd_unadjusted_var: NonLocalizedTextValue;
        rcd_adjusted: NonLocalizedTextValue;
        rcd_adjusted_var: NonLocalizedTextValue;
        rcd_lab_number: NonLocalizedTextValue;
        modified_by: NonLocalizedTextValue;
        modified_on: DateValue;
    };
}

export interface SiteDimensionsTile extends AliasedTileData {
    aliased_data: {
        length: NumberValue;
        dimension_entered_by: NonLocalizedTextValue;
        dimension_entered_date: DateValue;
        length_direction: NonLocalizedTextValue;
        width_direction: NonLocalizedTextValue;
        width: NumberValue;
        site_area: NumberValue;
        boundary_type: StringValue;
    };
}

export interface HriaDiscontinuedDataSchema extends AliasedTileData {
    aliased_data: {
        biogeography?: BiogeographyTile;
        unreviewed_adif_record?: UnreviewedAdifRecordTile;
        archaeological_site?: ArchaeologicalSiteTile;
        hria_jursidiction_and_tenure?: HriaJurisdictionAndTenureTile[];
        chronology?: ChronologyTile[];
        site_dimensions?: SiteDimensionsTile;
    };

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
