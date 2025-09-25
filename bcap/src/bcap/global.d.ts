import('@/arches/declarations.d.ts');

declare module 'underscore';
declare module 'arches';
declare module 'utils/map-popup-provider';

declare module '@/bcgov_arches_common/datatypes/geojson-feature-collection/types.ts' {
    export interface AliasedGeojsonFeatureCollectionNode {
        node_value: unknown;
        display_value: string;
        details: unknown[];
    }
}

declare module '@/bcgov_arches_common/components/SimpleMap/SimpleMap.vue' {
    const component: unknown;
    export default component;
}
