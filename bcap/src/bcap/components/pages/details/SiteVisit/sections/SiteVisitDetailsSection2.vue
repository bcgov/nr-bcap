<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";
import EmptyState from "@/bcap/components/EmptyState.vue";
import StandardDataTable from "@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue";
import type { SiteVisitSchema } from "@/bcap/schema/SiteVisitSchema.ts";

const props = withDefaults(
    defineProps<{ data: SiteVisitSchema | undefined; loading?: boolean }>(),
    { loading: false },
);

const idTile = computed(() => props.data?.aliased_data?.identification);
const tempNumber = computed(() => idTile.value?.aliased_data?.temporary_number);
const newNames = computed(
    () => idTile.value?.aliased_data?.new_site_names || [],
);

const hasTemporaryNumber = computed(() => {
    return tempNumber.value?.aliased_data?.temporary_number?.node_value;
});

const hasNewNames = computed(() => {
    return newNames.value && newNames.value.length > 0;
});

const newNameColumns = [
    { field: "name", label: "Site Name" },
    { field: "name_type", label: "Site Name Type" },
    { field: "name_remarks", label: "Site Name Remarks" },
    { field: "assigned_or_reported_date", label: "Date Assigned or Reported" },
    { field: "assigned_or_reported_by", label: "Assigned or Reported By" },
    { field: "entered_on", label: "Entered On" },
    { field: "entered_by", label: "Entered By" },
];
</script>

<template>
    <DetailsSection
        section-title="2. Identification"
        :visible="true"
        :loading="props.loading"
    >
        <template #sectionContent>
            <DetailsSection
                section-title="Temporary Numbers"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasTemporaryNumber }"
            >
                <template #sectionContent>
                    <div v-if="tempNumber">
                        <dl>
                            <dt>Temporary Number</dt>
                            <dd>
                                {{
                                    tempNumber?.aliased_data?.temporary_number
                                        ?.display_value
                                }}
                            </dd>
                            <dt>Assigned By</dt>
                            <dd>
                                {{
                                    tempNumber?.aliased_data
                                        ?.temporary_number_assigned_by?.display_value
                                }}
                            </dd>
                            <dt>Assigned Date</dt>
                            <dd>
                                {{
                                    tempNumber?.aliased_data
                                        ?.temporary_number_assigned_date?.display_value
                                }}
                            </dd>
                        </dl>
                    </div>
                    <EmptyState
                        v-else
                        message="No temporary number assigned."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="New Site Names"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasNewNames }"
            >
                <template #sectionContent>
                    <div v-if="hasNewNames">
                        <StandardDataTable
                            :table-data="newNames"
                            :column-definitions="newNameColumns"
                            title="New Site Names"
                        />
                    </div>
                    <EmptyState
                        v-else
                        message="No new site names recorded."
                    />
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>

<style scoped></style>
