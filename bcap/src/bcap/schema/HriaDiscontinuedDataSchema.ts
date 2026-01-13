import type { AliasedTileData } from '@/arches_component_lab/types.ts';
import type { StringValue } from '@/arches_component_lab/datatypes/string/types.ts';
import type { NonLocalizedTextValue } from '@/arches_component_lab/datatypes/non-localized-text/types.ts';
import type { DateValue } from '@/arches_component_lab/datatypes/date/types.ts';
import type { ResourceInstanceListValue } from '@/arches_component_lab/datatypes/resource-instance-list/types.ts';
import type { ReferenceSelectValue } from '@/arches_controlled_lists/datatypes/reference-select/types.js';
import type {
    NumberValue,
    NullableReferenceSelectValue,
} from '@/bcap/types.ts';

export interface BiogeographyTile extends AliasedTileData {
    aliased_data: {
        biogeography_description: StringValue;
        biogeography_entered_by: NonLocalizedTextValue;
        biogeography_entered_date: DateValue;
        biogeography_name: StringValue;
        biogeography_type: NonLocalizedTextValue;
    };
}

export interface UnreviewedAdifRecordTile extends AliasedTileData {
    aliased_data: {
        site_entered_by: NonLocalizedTextValue;
        site_entry_date: DateValue;
        unreviewed_adif_record: NonLocalizedTextValue;
    };
}

export interface ArchaeologicalSiteTile extends AliasedTileData {
    aliased_data: {
        archaeological_site: ResourceInstanceListValue;
    };
}

export interface HriaJurisdictionAndTenureTile extends AliasedTileData {
    aliased_data: {
        jurisdiction_entered_by: StringValue;
        jurisdiction_entered_date: DateValue;
        site_jurisdiction: StringValue;
        tenure_identifier: StringValue;
        tenure_remarks: StringValue;
        tenure_type: StringValue;
    };
}

export interface ChronologyTile extends AliasedTileData {
    aliased_data: {
        chronology_modified_by: NonLocalizedTextValue;
        chronology_modified_on: DateValue;
        chronology_remarks: StringValue;
        determination_method: ReferenceSelectValue;
        end_year: DateValue;
        end_year_calendar: ReferenceSelectValue;
        end_year_qualifier: NullableReferenceSelectValue;
        information_source: StringValue;
        rcd_adjusted: NonLocalizedTextValue;
        rcd_adjusted_var: NonLocalizedTextValue;
        rcd_lab_code: NonLocalizedTextValue;
        rcd_lab_number: NonLocalizedTextValue;
        rcd_unadjusted: NonLocalizedTextValue;
        rcd_unadjusted_var: NonLocalizedTextValue;
        start_year: DateValue;
        start_year_calendar: ReferenceSelectValue;
        start_year_qualifier: NullableReferenceSelectValue;
    };
}

export interface SiteDimensionsTile extends AliasedTileData {
    aliased_data: {
        boundary_type: StringValue;
        dimension_entered_by: NonLocalizedTextValue;
        dimension_entered_date: DateValue;
        length: NumberValue;
        length_direction: NonLocalizedTextValue;
        site_area: NumberValue;
        width: NumberValue;
        width_direction: NonLocalizedTextValue;
    };
}

export interface DiscontinuedAddressAttributesTile extends AliasedTileData {
    aliased_data: {
        city: StringValue;
        discontinued_address_attributes?: DiscontinuedAddressAttributesTile[];
        legal_description: StringValue;
        legal_number: StringValue;
        legal_type: StringValue;
        modified_by: NonLocalizedTextValue;
        modified_on: DateValue;
        pid: StringValue;
        pin: StringValue;
        postal_code: StringValue;
        street_name: StringValue;
        street_number: StringValue;
    };
}

export interface OtherMapsTile extends AliasedTileData {
    aliased_data: {
        other_maps_map_name: StringValue;
        other_maps_map_scale: StringValue;
        other_maps_modified_by: ResourceInstanceListValue;
        other_maps_modified_on: DateValue;
    };
}

export interface SiteBoundaryAnnotationsTile extends AliasedTileData {
    aliased_data: {
        accuracy_remarks: StringValue;
        site_boundary_entered_by: NonLocalizedTextValue;
        site_boundary_entered_on: DateValue;
        source_notes: StringValue;
    };
}

export interface HriaDiscontinuedDataSchema extends AliasedTileData {
    aliased_data: {
        archaeological_site?: ArchaeologicalSiteTile;
        biogeography?: BiogeographyTile[];
        chronology?: ChronologyTile[];
        hria_jursidiction_and_tenure?: HriaJurisdictionAndTenureTile[];
        other_maps?: OtherMapsTile[];
        site_boundary_annotations?: SiteBoundaryAnnotationsTile[];
        site_dimensions?: SiteDimensionsTile;
        unreviewed_adif_record?: UnreviewedAdifRecordTile;
    };

    createdtime: string;
    descriptors: Record<
        string,
        { description: string; map_popup: string; name: string }
    >;
    graph: string;
    graph_has_different_publication: boolean;
    graph_publication: string;
    legacyid: string;
    name: string;
    principaluser: string | null;
    resource_instance_lifecycle_state: string;
}
