<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";
// main.js or in your component's script setup
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
</template>
