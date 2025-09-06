<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";
import type { SiteVisitSchema } from "@/bcap/schema/SiteVisitSchema.ts";

const props = withDefaults(
    defineProps<{ data: SiteVisitSchema | undefined }>(),
    {},
);
const current = computed(() => props.data);
</script>

<template>
    <DetailsSection
        section-title="1. Site Visit Location"
        :visible="true"
    >
        <template #sectionContent>
            <div>
                <dl>
                    <dt>1.1 Location and Access</dt>
                    <dd>
                        {{
                            current.value?.aliased_data?.site_visit_location
                                ?.aliased_data?.location_and_access
                                ?.display_value
                        }}
                    </dd>

                    <dt>1.2 Site Visit Location (geojson)</dt>
                    <dd>
                        <pre
                            style="
                                white-space: pre-wrap;
                                word-break: break-word;
                            "
                            >{{
                                JSON.stringify(
                                    current.value?.aliased_data
                                        ?.site_visit_location?.aliased_data
                                        ?.site_visit_location?.node_value,
                                    null,
                                    2,
                                )
                            }}
            </pre
                        >
                    </dd>

                    <dt
                        v-if="
                            current.value?.aliased_data?.site_visit_location
                                ?.aliased_data?.latest_edit_type?.node_value
                        "
                    >
                        1.3 Latest Edit Type
                    </dt>
                    <dd
                        v-if="
                            current.value?.aliased_data?.site_visit_location
                                ?.aliased_data?.latest_edit_type?.node_value
                        "
                    >
                        {{
                            current.value?.aliased_data?.site_visit_location
                                ?.aliased_data?.latest_edit_type?.display_value
                        }}
                    </dd>

                    <dt>1.4 Accuracy Remarks</dt>
                    <dd>
                        {{
                            current.value?.aliased_data?.site_visit_location
                                ?.aliased_data?.accuracy_remarks?.display_value
                        }}
                    </dd>

                    <dt>1.5 Source Notes</dt>
                    <dd>
                        {{
                            current.value?.aliased_data?.site_visit_location
                                ?.aliased_data?.source_notes?.display_value
                        }}
                    </dd>
                </dl>
            </div>
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
