import type {
    AliasedNodeData,
    AliasedTileData,
} from '@/arches_component_lab/types.ts';

export interface RepositoryIdentifierTile extends AliasedTileData {
    aliased_data: {
        repository_name?: AliasedNodeData;
        repository_location_code?: AliasedNodeData;
        alternate_identifiers?: AliasedTileData[];
    };
}

export interface ContactInformationTile extends AliasedTileData {
    aliased_data: {
        contact_person?: AliasedNodeData;
        contact_email?: AliasedNodeData;
        contact_phone?: AliasedNodeData;
    };
}

export interface RepositorySchema extends AliasedTileData {
    aliased_data: {
        repository_identifier?: RepositoryIdentifierTile;
        contact_information?: ContactInformationTile | null;
        repository_notes?: AliasedTileData[];
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
