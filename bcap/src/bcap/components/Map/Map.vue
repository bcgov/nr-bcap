<script setup lang="ts">
import { fetchSystemMapData } from "@/bcap/components/Map/api.ts";
import { ref, onMounted } from "vue";

import type { AliasedGeojsonFeatureCollectionNode } from "@/bcgov_arches_common/datatypes/geojson-feature-collection/types.ts";
import { VIEW } from "@/arches_component_lab/widgets/constants.ts";
import type { WidgetMode } from "@/arches_component_lab/widgets/types.ts";
import type { MapData } from "@/bcgov_arches_common/datatypes/geojson-feature-collection/types.ts";

import MapView from "@/bcap/components/Map/components/MapView.vue";

const mapData = ref<MapData>({} as MapData);
const { mode, aliasedNodeData } = defineProps<{
    mode: WidgetMode;
    aliasedNodeData: AliasedGeojsonFeatureCollectionNode;
}>();

onMounted(async () => {
    mapData.value = await fetchSystemMapData();
});
</script>
<template>
    <MapView
        v-if="mode === VIEW"
        :map-data="mapData"
        :aliased-node-data="aliasedNodeData"
    ></MapView>
</template>
