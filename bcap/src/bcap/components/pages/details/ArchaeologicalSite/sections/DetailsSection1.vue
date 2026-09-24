<script setup lang="ts">
import { computed, type Ref } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import EmptyState from '@/bcap/components/EmptyState.vue';
import { VIEW } from '@/arches_vue_components/widgets/constants.ts';
import 'primeicons/primeicons.css';
import type { AliasedGeojsonFeatureCollectionNode } from '@/bcgov_arches_common/datatypes/geojson-feature-collection/types.ts';

import Map from '@/bcgov_arches_common/widgets/SimpleMapWidget/SimpleMapWidget.vue';

import 'maplibre-gl/dist/maplibre-gl.css';

import type {
    ArchaeologicalSite,
    ArchaeologicalSiteSiteBoundaryTile,
} from '@/bcap/client/types.gen.ts';

import { useMapFrameAutoCentre } from '@/bcgov_arches_common/composables/useMapFrameAutoCentre.ts';

const props = withDefaults(
    defineProps<{
        data: ArchaeologicalSite | undefined;
        loading?: boolean;
        languageCode?: string;
        forceCollapsed?: boolean;
    }>(),
    {
        loading: false,
        languageCode: 'en',
        forceCollapsed: undefined,
    },
);

useMapFrameAutoCentre('mapBoxes', { showCentroidMarker: false });

const siteBoundary = computed<ArchaeologicalSiteSiteBoundaryTile | undefined>(
    (): ArchaeologicalSiteSiteBoundaryTile | undefined => {
        return props.data?.aliased_data?.site_boundary as
            ArchaeologicalSiteSiteBoundaryTile | undefined;
    },
);

const hasGeoJsonData = computed(() => {
    return siteBoundary.value?.aliased_data?.site_boundary?.node_value;
});

const siteBoundaryNode = computed<
    AliasedGeojsonFeatureCollectionNode | undefined
>((): AliasedGeojsonFeatureCollectionNode | undefined => {
    return (siteBoundary as Ref<ArchaeologicalSiteSiteBoundaryTile>)?.value
        ?.aliased_data?.site_boundary as
        AliasedGeojsonFeatureCollectionNode | undefined;
});
</script>

<template>
    <div
        ref="mapBoxes"
        style="--map-max-width: 100%"
    >
        <Map
            graph-slug="archaeological_site"
            node-alias="site_boundary"
            :mode="VIEW"
            :aliased-node-data="
                siteBoundaryNode as AliasedGeojsonFeatureCollectionNode
            "
            :use-utm-coords="true"
        ></Map>
    </div>
    <DetailsSection
        section-title="1. Spatial View"
        :visible="true"
        :loading="props.loading"
        :force-collapsed="props.forceCollapsed"
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
                            }}</pre>
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
