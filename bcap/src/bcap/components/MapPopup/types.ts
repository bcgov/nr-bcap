import type { Ref } from 'vue';

export type DescriptorsType = {
    displayname: string;
    graph_name: string;
    map_popup: string;
    description: string;
};

export type DescriptorKey = keyof DescriptorsType; // "displayname" | "graph_name" | "map_popup" | "description"

// make sure these are typed as keys of DescriptorsType
export const descriptionProperties: DescriptorKey[] = [
    'displayname',
    'graph_name',
    'map_popup',
    'description',
];

export type PermissionsType = {
    principal_user: Array<unknown>;
    users_with_no_access: Array<unknown>;
    users_without_delete_perm: Array<unknown>;
    users_without_edit_perm: Array<unknown>;
    users_without_read_perm: Array<unknown>;
};

export type MapCardType = {
    showDetailsFromFilter: (arg0: string) => void;
};

export type PopupFeatureType = {
    active: () => boolean;
    displayValues: DescriptorsType | Ref<DescriptorsType>;
    editURL: string;
    featureid: string;
    map_popup: () => string;
    mapCard: MapCardType;
    permissions: PermissionsType;
    showAll: () => boolean;
    showEditButton: () => boolean;
    showExpandButton: () => boolean;
    showFilterByFeature: (arg0: PopupFeatureType) => boolean;
    showFilterByFeatureButton: boolean;
    loading: boolean;
    resourceinstanceid: string;
    reportURL: string;
    toggleShowAll: () => void;
    tileid: string;
    total: number;
};

export interface Translations {
    edit: string;
    report: string;
    idString: string;
    of: string;
    filterByFeature: string;
    resourceModel: string;
    loading: string;
}
