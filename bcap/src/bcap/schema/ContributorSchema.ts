import type {
    AliasedNodeData,
    AliasedTileData,
} from '@/arches_component_lab/types.ts';

export interface ContributorTile extends AliasedTileData {
    aliased_data: {
        first_name?: AliasedNodeData;
        contributor_name?: AliasedNodeData;
        contact_phone_number?: AliasedNodeData;
        contact_email?: AliasedNodeData;
        inactive?: AliasedNodeData;
        contributor_role?: AliasedNodeData;
        contributor_type?: AliasedNodeData;
    };
}

export interface AssociatedOrganizationTile extends AliasedTileData {
    aliased_data: {
        end_date?: AliasedNodeData;
        start_date?: AliasedNodeData;
        associated_organization?: AliasedNodeData;
    };
}

export interface ContributorSchema extends AliasedTileData {
    aliased_data: {
        contributor?: ContributorTile;
        associated_organization?: AssociatedOrganizationTile[];
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
