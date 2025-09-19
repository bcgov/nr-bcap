import type {
    AliasedNodeData,
    AliasedTileData,
} from "@/arches_component_lab/types.ts";

export interface LegislativeActTile extends AliasedTileData {
    aliased_data: {
        act_name?: AliasedNodeData;
        act_type?: AliasedNodeData;
        jurisdiction?: AliasedNodeData;
        act_description?: AliasedNodeData;
        enactment_date?: AliasedNodeData;
        repeal_date?: AliasedNodeData;
        act_status?: AliasedNodeData;
        act_citation?: AliasedNodeData;
        responsible_ministry?: AliasedNodeData;
    };
}

export interface LegislativeActSchema extends AliasedTileData {
    aliased_data: {
        legislative_act?: LegislativeActTile;
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
