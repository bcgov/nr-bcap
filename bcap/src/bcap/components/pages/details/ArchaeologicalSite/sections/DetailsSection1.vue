<script setup lang="ts">
import { computed } from "vue";
import type { Ref } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";
import { VIEW } from "@/arches_component_lab/widgets/constants.ts";
// import InteractiveMap from "@/bcgov_arches_common/components/Search/components/InteractiveMap/InteractiveMap.vue";
// import SearchPage from "@/bcgov_arches_common/components/Search/SearchPage.vue";
// import Toast from "primevue/toast";
// import { useToast } from "primevue/usetoast";
// import { useGettext } from "vue3-gettext";
// main.js or in your component's script setup
import "primeicons/primeicons.css";
// import type { GenericObject } from "@/bcgov_arches_common/components/Search/types.ts";
//
import type { AliasedGeojsonFeatureCollectionNode } from "@/bcgov_arches_common/datatypes/geojson-feature-collection/types.ts";

import Map from "@/bcap/components/Map/Map.vue";

// import {
//     DEFAULT_ERROR_TOAST_LIFE,
//     ERROR,
// } from "@/bcgov_arches_common/components/Search/constants.ts";

import "maplibre-gl/dist/maplibre-gl.css";

import type {
    ArchaeologySiteSchema,
    SiteBoundaryTile,
} from "@/bcap/schema/ArchaeologySiteSchema.ts";

const props = withDefaults(
    defineProps<{
        data: ArchaeologySiteSchema | undefined;
        loading?: boolean;
        languageCode?: string;
    }>(),
    {
        loading: false,
        languageCode: "en",
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

const siteBoundaryNode = computed<
    AliasedGeojsonFeatureCollectionNode | undefined
>((): AliasedGeojsonFeatureCollectionNode | undefined => {
    return (siteBoundary as Ref<SiteBoundaryTile>)?.value?.aliased_data
        ?.site_boundary as AliasedGeojsonFeatureCollectionNode | undefined;
});
</script>

<template>
    <Map
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
                :visible="false"
            >
                <template #sectionContent>
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
                </template>
            </DetailsSection>
            <div>
                <dl>
                    <dt>Accuracy Remarks</dt>
                    <dd>
                        {{
                            siteBoundary?.aliased_data.accuracy_remarks
                                ?.display_value
                        }}
                    </dd>
                    <dt>Source Notes</dt>
                    <dd>
                        {{
                            siteBoundary?.aliased_data.source_notes
                                ?.display_value
                        }}
                    </dd>
                    <div
                        v-if="
                            siteBoundary?.aliased_data?.latest_edit_type
                                ?.node_value
                        "
                    >
                        <dt>Latest Edit Type</dt>
                        <dd>
                            {{
                                siteBoundary?.aliased_data?.latest_edit_type
                                    ?.display_value
                            }}
                        </dd>
                    </div>
                </dl>
            </div>
        </template>
    </DetailsSection>
    <!--    <Toast />-->
</template>
