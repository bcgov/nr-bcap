import type {
    MapLayer,
    MapSource,
} from "@/bcgov_arches_common/datatypes/geojson-feature-collection/types.ts";
import { map, object } from "underscore";
import type { MapData } from "@/bcgov_arches_common/datatypes/geojson-feature-collection/types.ts";

import { fetchMapData } from "@/bcgov_arches_common/datatypes/geojson-feature-collection/api.ts";
import type { FeatureCollection } from "geojson";

export async function fetchSystemMapData() {
    const transformedMapData: MapData = {
        overlays: [],
        basemaps: [],
        default_bounds: {} as FeatureCollection,
    };
    try {
        const mapData = await fetchMapData();
        const layers = mapData.map_layers;
        transformedMapData.default_bounds = mapData.default_bounds;

        const sourcesMap = object(
            map(mapData.map_sources, function (item: MapSource) {
                return [item.name, item];
            }),
        );

        mapData.map_layers.forEach((layer: MapLayer) => {
            layer.source = sourcesMap[layer.layerdefinitions?.[0].source];
        });

        transformedMapData.overlays = layers.filter(
            (layer: MapLayer) => layer.isoverlay,
        );
        transformedMapData.basemaps = layers.filter(
            (layer: MapLayer) => !layer.isoverlay,
        );

        transformedMapData.overlays.sort(
            (a, b) => (b.sortorder ?? 0) - (a.sortorder ?? 0),
        );
        transformedMapData.basemaps.sort(
            (a, b) => (b.sortorder ?? 0) - (a.sortorder ?? 0),
        );

        return transformedMapData;
    } catch (error) {
        console.log(error);
    }
}
