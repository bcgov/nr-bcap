import type {
    AliasedNodeData,
    AliasedTileData,
} from '@/arches_component_lab/types.ts';

export interface PermitIdentificationTile extends AliasedTileData {
    aliased_data: {
        permit_holder?: AliasedNodeData;
        permit_number?: AliasedNodeData;
        hca_permit_type?: AliasedNodeData;
        issuing_agency?: AliasedNodeData;
    };
}

export interface HcaPermitSchema extends AliasedTileData {
    aliased_data: {
        permit_identification?: PermitIdentificationTile;
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
