<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";
import EmptyState from "@/bcap/components/EmptyState.vue";
import "primeicons/primeicons.css";
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

const hasBoundaryInfo = computed(() => {
    return (
        siteBoundary.value?.aliased_data?.accuracy_remarks?.display_value ||
        siteBoundary.value?.aliased_data?.source_notes?.display_value ||
        siteBoundary.value?.aliased_data?.latest_edit_type?.node_value
    );
});
</script>

<template>
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

            <DetailsSection
                section-title="Site Boundary Information"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasBoundaryInfo }"
            >
                <template #sectionContent>
                    <div v-if="hasBoundaryInfo">
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
                                        siteBoundary?.aliased_data
                                            ?.latest_edit_type?.display_value
                                    }}
                                </dd>
                            </div>
                        </dl>
                    </div>
                    <EmptyState
                        v-else
                        message="No site boundary information available."
                    />
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>
