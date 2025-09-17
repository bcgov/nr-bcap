<script setup lang="ts">
import maplibregl, {
    type LayerSpecification,
    type Map as MapLibreMap,
} from "maplibre-gl";
import { watch, onMounted, type Ref, ref, shallowRef, computed } from "vue";
import type { MapData } from "@/bcap/components/Map/types.ts";
import centroid from "@turf/centroid";
import bbox from "@turf/bbox";
import { find } from "underscore";
import type { AliasedGeojsonFeatureCollectionNode } from "@/bcgov_arches_common/datatypes/geojson-feature-collection/types.ts";
import type { FeatureCollection } from "geojson";
import type { AllGeoJSON } from "@turf/helpers";
import type {
    MapSource,
    MapLayer,
} from "@/bcgov_arches_common/datatypes/geojson-feature-collection/types.ts";

const props = defineProps<{
    mapData: MapData;
    aliasedNodeData: AliasedGeojsonFeatureCollectionNode;
}>();

const geometry = computed<FeatureCollection | undefined>(() => {
    return props.aliasedNodeData?.node_value?.features?.[0];
});

const hasGeometry = computed<boolean>(() => {
    return geometry.value !== undefined;
});

const mapLoaded = ref(false);

const center = ref<[number, number]>([-123.1207, 49.2827]); // Vancouver (lng, lat)
const mapCentre = computed<[number, number]>(() => {
    return (
        props.aliasedNodeData?.node_value
            ? (centroid(geometry.value as AllGeoJSON)?.geometry?.coordinates ??
              center.value)
            : center.value
    ) as [number, number];
});

const zoom = ref<number>(3.5);

const mapEl = ref<HTMLDivElement | null>(null);
const map: Ref<MapLibreMap | null> = ref(null);

const styleObj = {
    version: 8,
    name: "Custom WMS Basemap + Overlays",
    sources: {} as MapSource,
    layers: [] as LayerSpecification[],
    // Optional: wire up glyphs/sprite if you also use symbol layers elsewhere
    glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
} satisfies maplibregl.StyleSpecification;

const defaultStyle = shallowRef<maplibregl.StyleSpecification>(styleObj);

function setupMap(): void {
    // dataLoaded.value = true;
    if (!mapEl.value) return;

    const basemap = find(props.mapData.basemaps, (basemap: MapLayer) => {
        return basemap.addtomap;
    });
    defaultStyle.value.sources[basemap.source.name] = basemap.source.source;
    defaultStyle.value.layers.push(...basemap.layerdefinitions);
    if (props.mapData.default_bounds)
        center.value = centroid(
            props.mapData.default_bounds as AllGeoJSON,
        ).geometry.coordinates;
    map.value = new maplibregl.Map({
        container: mapEl.value,
        style: defaultStyle.value,
        center: mapCentre.value,
        zoom: zoom.value,
        attributionControl: false,
    });

    map.value.on("load", () => {
        mapLoaded.value = true;
        map.value?.addControl(
            new maplibregl.NavigationControl({ visualizePitch: true }),
            "top-right",
        );
        map.value?.addControl(
            new maplibregl.ScaleControl({ maxWidth: 120, unit: "metric" }),
        );
        map.value?.addControl(
            new maplibregl.AttributionControl({ compact: true }),
        );
        if (props.aliasedNodeData?.node_value?.features?.[0]) {
            console.log("Adding geometry from load event");
            addGeometryToMap(props.aliasedNodeData.node_value.features[0]);
        }
    });

    map.value.on("moveend", () => {
        if (!map.value) return;
        const c = map.value.getCenter();
        center.value = [Number(c.lng.toFixed(5)), Number(c.lat.toFixed(5))];
        zoom.value = Number(map.value.getZoom().toFixed(2));
    });

    const onResize = () => map.value && map.value.resize();
    window.addEventListener("resize", onResize);
    (map.value as MapLibreMap).__onResize = onResize;
}

onMounted(async () => {
    if (!map.value && props.mapData.value) {
        setupMap();
    }
});

watch(
    () => props.mapData,
    (mapData, prevMapData) => {
        if (mapData) {
            setupMap(mapData);
        }
    },
);

watch(mapCentre, (val, oldVal) => {
    if (map.value && oldVal) {
        map.value.flyTo({ center: val, zoom: zoom.value, speed: 0.8 });
    }
});

const addGeometryToMap = (feature) => {
    if (!map.value || !hasGeometry.value || !mapLoaded.value) return;

    map.value.addSource(feature.id, {
        type: "geojson",
        data: feature.geometry,
    });

    map.value.addLayer({
        id: `${feature.id}-site`,
        type: "line",
        source: feature.id,
    });

    new maplibregl.Marker({ color: "#d97706" })
        .setLngLat(mapCentre.value)
        .setPopup(new maplibregl.Popup().setHTML("<b>Feature centroid</b>"))
        .addTo(map.value);

    const bounds = bbox(feature.geometry);
    map.value.fitBounds(
        [
            [bounds[0], bounds[1]],
            [bounds[2], bounds[3]],
        ],
        {
            padding: 100,
            maxZoom: 15,
        },
    );

    center.value = mapCentre.value;
    console.log("New centre value: ", center.value);
};

watch(
    () => props.aliasedNodeData?.node_value?.features?.[0],
    (feature, prevFeature) => {
        if (feature && map.value) {
            console.log("Adding geometry from watch event");
            addGeometryToMap(feature);
        }
    },
);
</script>
<template>
    <div class="map-wrap">
        <div
            ref="mapEl"
            class="map"
            style="min-height: 300px"
        ></div>
        <div class="panel">
            <!--button @click="flyVancouver">Vancouver</button>
            <button @click="flyParis">Paris</button-->
            <span class="coords">
                Boundary Centroid Lng/Lat: {{ mapCentre?.[0].toFixed(6) }},
                {{ mapCentre?.[1].toFixed(6) }} | Zoom:
                {{ zoom }}
            </span>
        </div>
    </div>
</template>
