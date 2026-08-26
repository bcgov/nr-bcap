import type { AliasedTileData } from '@/arches_vue_components/types.ts';
import type { StringAliasedNodeData } from '@/arches_vue_components/datatypes/string/types.ts';
import type { NonLocalizedTextAliasedNodeData } from '@/arches_vue_components/datatypes/non-localized-text/types.ts';
import type { DateAliasedNodeData } from '@/arches_vue_components/datatypes/date/types.ts';
import type { ResourceInstanceListAliasedNodeData } from '@/arches_vue_components/datatypes/resource-instance-list/types.ts';
import type { ReferenceSelectAliasedNodeData } from '@/arches_controlled_lists/datatypes/reference-select/types.js';
import type { NumberAliasedNodeData } from '@/arches_vue_components/datatypes/number/types.ts';

export interface BiogeographyTile extends AliasedTileData {
    aliased_data: {
        biogeography_description: StringAliasedNodeData;
        biogeography_entered_by: NonLocalizedTextAliasedNodeData;
        biogeography_entered_date: DateAliasedNodeData;
        biogeography_name: StringAliasedNodeData;
        biogeography_type: NonLocalizedTextAliasedNodeData;
    };
}

export interface UnreviewedAdifRecordTile extends AliasedTileData {
    aliased_data: {
        site_entered_by: NonLocalizedTextAliasedNodeData;
        site_entry_date: DateAliasedNodeData;
        unreviewed_adif_record: NonLocalizedTextAliasedNodeData;
    };
}

export interface ArchaeologicalSiteTile extends AliasedTileData {
    aliased_data: {
        archaeological_site: ResourceInstanceListAliasedNodeData;
    };
}

export interface HriaJurisdictionAndTenureTile extends AliasedTileData {
    aliased_data: {
        jurisdiction_entered_by: StringAliasedNodeData;
        jurisdiction_entered_date: DateAliasedNodeData;
        site_jurisdiction: StringAliasedNodeData;
        tenure_identifier: StringAliasedNodeData;
        tenure_remarks: StringAliasedNodeData;
        tenure_type: StringAliasedNodeData;
    };
}

export interface ChronologyTile extends AliasedTileData {
    aliased_data: {
        chronology_modified_by: NonLocalizedTextAliasedNodeData;
        chronology_modified_on: DateAliasedNodeData;
        chronology_remarks: StringAliasedNodeData;
        determination_method: ReferenceSelectAliasedNodeData;
        end_year: DateAliasedNodeData;
        end_year_calendar: ReferenceSelectAliasedNodeData;
        end_year_qualifier: ReferenceSelectAliasedNodeData;
        information_source: StringAliasedNodeData;
        rcd_adjusted: NonLocalizedTextAliasedNodeData;
        rcd_adjusted_var: NonLocalizedTextAliasedNodeData;
        rcd_lab_code: NonLocalizedTextAliasedNodeData;
        rcd_lab_number: NonLocalizedTextAliasedNodeData;
        rcd_unadjusted: NonLocalizedTextAliasedNodeData;
        rcd_unadjusted_var: NonLocalizedTextAliasedNodeData;
        start_year: DateAliasedNodeData;
        start_year_calendar: ReferenceSelectAliasedNodeData;
        start_year_qualifier: ReferenceSelectAliasedNodeData;
    };
}

export interface SiteDimensionsTile extends AliasedTileData {
    aliased_data: {
        boundary_type: StringAliasedNodeData;
        dimension_entered_by: NonLocalizedTextAliasedNodeData;
        dimension_entered_date: DateAliasedNodeData;
        length: NumberAliasedNodeData;
        length_direction: NonLocalizedTextAliasedNodeData;
        site_area: NumberAliasedNodeData;
        width: NumberAliasedNodeData;
        width_direction: NonLocalizedTextAliasedNodeData;
    };
}

export interface DiscontinuedAddressAttributesTile extends AliasedTileData {
    aliased_data: {
        city: StringAliasedNodeData;
        discontinued_address_attributes?: DiscontinuedAddressAttributesTile[];
        legal_description: StringAliasedNodeData;
        legal_number: StringAliasedNodeData;
        legal_type: StringAliasedNodeData;
        modified_by: NonLocalizedTextAliasedNodeData;
        modified_on: DateAliasedNodeData;
        pid: StringAliasedNodeData;
        pin: StringAliasedNodeData;
        postal_code: StringAliasedNodeData;
        street_name: StringAliasedNodeData;
        street_number: StringAliasedNodeData;
    };
}

export interface OtherMapsTile extends AliasedTileData {
    aliased_data: {
        other_maps_map_name: StringAliasedNodeData;
        other_maps_map_scale: StringAliasedNodeData;
        other_maps_modified_by: StringAliasedNodeData;
        other_maps_modified_on: DateAliasedNodeData;
    };
}

export interface SiteBoundaryAnnotationsTile extends AliasedTileData {
    aliased_data: {
        accuracy_remarks: StringAliasedNodeData;
        site_boundary_entered_by: NonLocalizedTextAliasedNodeData;
        site_boundary_entered_on: DateAliasedNodeData;
        source_notes: StringAliasedNodeData;
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
