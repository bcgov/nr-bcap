<script setup lang="ts">
import { computed, Ref } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import EmptyState from '@/bcap/components/EmptyState.vue';
import { VIEW } from '@/arches_component_lab/widgets/constants.ts';
// import InteractiveMap from "@/bcgov_arches_common/components/Search/components/InteractiveMap/InteractiveMap.vue";
// import SearchPage from "@/bcgov_arches_common/components/Search/SearchPage.vue";
// import Toast from "primevue/toast";
// import { useToast } from "primevue/usetoast";
// import { useGettext } from "vue3-gettext";
// main.js or in your component's script setup
import 'primeicons/primeicons.css';
// import type { GenericObject } from "@/bcgov_arches_common/components/Search/types.ts";
//
import type { AliasedGeojsonFeatureCollectionNode } from '@/bcgov_arches_common/datatypes/geojson-feature-collection/types.ts';

import Map from '@/bcgov_arches_common/components/SimpleMap/SimpleMap.vue';

// import {
//     DEFAULT_ERROR_TOAST_LIFE,
//     ERROR,
// } from "@/bcgov_arches_common/components/Search/constants.ts";

import 'maplibre-gl/dist/maplibre-gl.css';

import type {
    ArchaeologySiteSchema,
    SiteBoundaryTile,
} from '@/bcap/schema/ArchaeologySiteSchema.ts';

const props = withDefaults(
    defineProps<{
        data: ArchaeologySiteSchema | undefined;
        loading?: boolean;
        languageCode?: string;
    }>(),
    {
        loading: false,
        languageCode: 'en',
    },
);

//
// const toast = useToast();
//
const siteBoundary = computed<SiteBoundaryTile | undefined>(
    (): SiteBoundaryTile | undefined => {
        return props.data?.aliased_data?.site_boundary as
            | SiteBoundaryTile
            | undefined;
    },
);

const hasGeoJsonData = computed(() => {
    return siteBoundary.value?.aliased_data?.site_boundary?.node_value;
});

const siteBoundaryNode = computed<
    AliasedGeojsonFeatureCollectionNode | undefined
>((): AliasedGeojsonFeatureCollectionNode | undefined => {
    return (siteBoundary as Ref<SiteBoundaryTile>)?.value?.aliased_data
        ?.site_boundary as AliasedGeojsonFeatureCollectionNode | undefined;
});
</script>

<template>
    <Map
        graph-slug="archaeological_site"
        node-alias="site_boundary"
        :mode="VIEW"
        :aliased-node-data="
            siteBoundaryNode as AliasedGeojsonFeatureCollectionNode
        "
    ></Map>
    <DetailsSection
        section-title="1. Spatial View"
        :visible="true"
        :loading="props.loading"
    >
        <template #sectionContent>
            <DetailsSection
                section-title="Site Boundary GeoJSON"
                variant="subsection"
                :visible="false"
                :class="{ 'empty-section': !hasGeoJsonData }"
            >
                <template #sectionContent>
                    <div v-if="hasGeoJsonData">
                        <pre
                            style="
                                white-space: pre-wrap;
                                word-break: break-word;
                                max-height: 50rem;
                            "
                            >{{
                                JSON.stringify(
                                    siteBoundary?.aliased_data?.site_boundary
                                        ?.node_value,
                                    null,
                                    2,
                                )
                            }}</pre
                        >
                    </div>
                    <EmptyState
                        v-else
                        message="No site boundary data available."
                    />
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
    <!--    <Toast />-->
</template>
