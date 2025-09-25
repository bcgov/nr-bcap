import type {
    AliasedNodeData,
    AliasedTileData,
} from '@/arches_component_lab/types.ts';

export interface GovernmentNameTile extends AliasedTileData {
    aliased_data: {
        government_name?: AliasedNodeData;
        government_type?: AliasedNodeData;
    };
}

export interface OfficeAddressTile extends AliasedTileData {
    aliased_data: {
        city?: AliasedNodeData;
        street_address?: AliasedNodeData;
        postal_code?: AliasedNodeData;
        province?: AliasedNodeData;
    };
}

export interface GovernmentBoundaryTile extends AliasedTileData {
    aliased_data: {
        government_boundary?: AliasedNodeData;
    };
}

export interface GovernmentLocationTile extends AliasedTileData {
    office_address?: OfficeAddressTile;
    government_boundary?: GovernmentBoundaryTile;
}

export interface GovernmentSchema extends AliasedTileData {
    aliased_data: {
        government_name?: GovernmentNameTile;
        government_location?: GovernmentLocationTile;
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
