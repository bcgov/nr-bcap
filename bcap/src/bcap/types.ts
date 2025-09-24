import type { AliasedNodeData } from '@/arches_component_lab/types.ts';

import type {
    ReferenceSelectValue,
    ReferenceSelectNodeValue,
    ReferenceSelectDetails,
} from '@/arches_controlled_lists/datatypes/reference-select/types.js';

export interface TileReference {
    resourceinstance_id: string;
    tileid: string;
    nodegroupid: string;
    data: object;
}

export interface DetailsData {
    resourceinstance_id: string;
    displayname: string;
    graph_slug: string;
}

export interface NumberValue extends AliasedNodeData {
    display_value: string;
    node_value: number | null;
    details: never[];
}

export interface BooleanValue extends AliasedNodeData {
    display_value: string;
    node_value: boolean | null;
    details: never[];
}

export interface GeoJSONFeatureCollectionValue extends AliasedNodeData {
    display_value: string;
    node_value: {
        type: 'FeatureCollection';
        features: unknown[];
    } | null;
    details: never[];
}

export type NullableReferenceSelectValue =
    | ReferenceSelectValue
    | (Omit<ReferenceSelectValue, 'node_value'> & {
          node_value: ReferenceSelectNodeValue[] | null;
          details: ReferenceSelectDetails[] | [];
      });
