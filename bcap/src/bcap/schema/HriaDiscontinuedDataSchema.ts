// ---------- Datatype-specific node values (from your bundles) ----------
import type { AliasedTileData } from '@/arches_component_lab/types.ts';
import type { StringValue } from '@/arches_component_lab/datatypes/string/types.ts';
import type { NonLocalizedTextValue } from '@/arches_component_lab/datatypes/non-localized-text/types.ts';
import type { DateValue } from '@/arches_component_lab/datatypes/date/types.ts';
import type { ResourceInstanceListValue } from '@/arches_component_lab/datatypes/resource-instance-list/types.ts';
import type { ReferenceSelectValue } from '@/arches_controlled_lists/datatypes/reference-select/types.js';
import type {
    NumberValue,
    BooleanValue,
    NullableReferenceSelectValue,
} from '@/bcap/types.ts';

// ====================================================================
// Tiles specialized to THIS JSON (with datatype-specific leaf nodes)
// ====================================================================

// aliased_data.biogeography
export interface BiogeographyTile extends AliasedTileData {
    aliased_data: {
        biogeography_type: NonLocalizedTextValue; // non-localized-string
        biogeography_entered_by: NonLocalizedTextValue; // non-localized-string
        biogeography_entered_date: DateValue; // date
        biogeography_name: StringValue; // string (i18n)
        biogeography_description: StringValue; // string (i18n)
    };
}

// aliased_data.unreviewed_adif_record
export interface UnreviewedAdifRecordTile extends AliasedTileData {
    aliased_data: {
        unreviewed_adif_record: BooleanValue; // boolean
        site_entered_by: NonLocalizedTextValue; // non-localized-string
        site_entry_date: DateValue; // date
    };
}

// aliased_data.archaeological_site
// Mapping says "resource-instance", but this payload shows an array.
// Support both single and array shapes via a union.
export interface ArchaeologicalSiteTile extends AliasedTileData {
    aliased_data: {
        archaeological_site: ResourceInstanceListValue;
    };
}

// aliased_data.hria_jursidiction_and_tenure[] (semantic)
export interface HriaJurisdictionAndTenureTile extends AliasedTileData {
    aliased_data: {
        site_jurisdiction: StringValue; // string (i18n)
        tenure_identifier: StringValue; // string (i18n)
        jurisdiction_entered_by: StringValue; // string (i18n)
        jurisdiction_entered_date: DateValue; // date
        tenure_type: StringValue; // string (i18n)
        tenure_remarks: StringValue; // string (i18n)
    };
}

// aliased_data.chronology[] (semantic)
export interface ChronologyTile extends AliasedTileData {
    aliased_data: {
        end_year_qualifier: NullableReferenceSelectValue; // reference (nullable in payload)
        end_year_calendar: ReferenceSelectValue; // reference
        determination_method: ReferenceSelectValue; // reference
        start_year: DateValue; // date
        end_year: DateValue; // date
        start_year_calendar: ReferenceSelectValue; // reference
        start_year_qualifier: NullableReferenceSelectValue; // reference (nullable in payload)
        information_source: StringValue; // string (i18n)
        chronology_remarks: StringValue; // string (i18n)
        rcd_lab_code: NonLocalizedTextValue; // non-localized-string
        rcd_unadjusted: NonLocalizedTextValue; // non-localized-string
        rcd_unadjusted_var: NonLocalizedTextValue; // non-localized-string
        rcd_adjusted: NonLocalizedTextValue; // non-localized-string
        rcd_adjusted_var: NonLocalizedTextValue; // non-localized-string
        rcd_lab_number: NonLocalizedTextValue; // non-localized-string
        modified_by: NonLocalizedTextValue; // non-localized-string
        modified_on: DateValue; // date
    };
}

// aliased_data.site_dimensions
export interface SiteDimensionsTile extends AliasedTileData {
    aliased_data: {
        length: NumberValue; // number
        dimension_entered_by: NonLocalizedTextValue; // non-localized-string
        dimension_entered_date: DateValue; // date
        length_direction: NonLocalizedTextValue; // non-localized-string
        width_direction: NonLocalizedTextValue; // non-localized-string
        width: NumberValue; // number
        site_area: NumberValue; // number
        boundary_type: StringValue; // string (i18n)
    };
}

// ====================================================================
// Top-level object for THIS JSON
// ====================================================================
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
    createdtime: string; // ISO timestamp
    graph: string;
    graph_publication: string;
    resource_instance_lifecycle_state: string;
    principaluser: string | null;
}
