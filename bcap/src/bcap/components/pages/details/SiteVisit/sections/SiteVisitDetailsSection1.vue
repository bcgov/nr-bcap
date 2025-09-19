<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";
import EmptyState from "@/bcap/components/EmptyState.vue";
import type { SiteVisitSchema } from "@/bcap/schema/SiteVisitSchema.ts";

const props = withDefaults(
    defineProps<{
        data: SiteVisitSchema | undefined;
        loading?: boolean;
    }>(),
    { loading: false },
);

const current = computed(() => props.data);

const hasLocationData = computed(() => {
    return current.value?.aliased_data?.site_visit_location?.aliased_data;
});

const hasLocationAndAccess = computed(() => {
    return current.value?.aliased_data?.site_visit_location?.aliased_data
        ?.location_and_access?.node_value;
});

const hasGeoJsonData = computed(() => {
    return current.value?.aliased_data?.site_visit_location?.aliased_data
        ?.site_visit_location?.node_value;
});
</script>

<template>
    <DetailsSection
        section-title="1. Site Visit Location"
        :loading="props.loading"
        :visible="true"
    >
        <template #sectionContent>
            <DetailsSection
                section-title="Location and Access"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasLocationAndAccess }"
            >
                <template #sectionContent>
                    <div v-if="hasLocationData">
                        <dl>
                            <dt>Location and Access</dt>
                            <dd>
                                {{
                                    current?.aliased_data?.site_visit_location
                                        ?.aliased_data?.location_and_access
                                        ?.display_value
                                }}
                            </dd>

                            <dt
                                v-if="
                                    current?.aliased_data?.site_visit_location
                                        ?.aliased_data?.latest_edit_type
                                        ?.node_value
                                "
                            >
                                Latest Edit Type
                            </dt>
                            <dd
                                v-if="
                                    current?.aliased_data?.site_visit_location
                                        ?.aliased_data?.latest_edit_type
                                        ?.node_value
                                "
                            >
                                {{
                                    current?.aliased_data?.site_visit_location
                                        ?.aliased_data?.latest_edit_type
                                        ?.display_value
                                }}
                            </dd>

                            <dt>Accuracy Remarks</dt>
                            <dd>
                                {{
                                    current?.aliased_data?.site_visit_location
                                        ?.aliased_data?.accuracy_remarks
                                        ?.display_value
                                }}
                            </dd>

                            <dt>Source Notes</dt>
                            <dd>
                                {{
                                    current?.aliased_data?.site_visit_location
                                        ?.aliased_data?.source_notes
                                        ?.display_value
                                }}
                            </dd>
                        </dl>
                    </div>
                    <EmptyState v-else />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Site Visit Location (GeoJSON)"
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
                            "
                            >{{
                                JSON.stringify(
                                    current?.aliased_data?.site_visit_location
                                        ?.aliased_data?.site_visit_location
                                        ?.node_value,
                                    null,
                                    2,
                                )
                            }}
            </pre
                        >
                    </div>
                    <EmptyState v-else />
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>

<style>
dl {
    display: flex;
    flex-direction: column;
    padding-bottom: 1rem;
}
dt {
    min-width: 20rem;
}
</style>
<style scoped></style>
