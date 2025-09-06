<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";

import StandardDataTable from "@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue";
import type { SiteVisitSchema } from "@/bcap/schema/SiteVisitSchema.ts";

const props = withDefaults(
    defineProps<{ data: SiteVisitSchema | undefined }>(),
    {},
);
const idTile = computed(() => props.data?.aliased_data?.identification);
const tempNumber = computed(() => idTile.value?.aliased_data?.temporary_number);
const newNames = computed(
    () => idTile.value?.aliased_data?.new_site_names || [],
);

const tempFields = [
    { field: "temporary_number", label: "Temporary Number" },
    { field: "temporary_number_assigned_by", label: "Assigned By" },
    { field: "temporary_number_assigned_date", label: "Assigned Date" },
];

const newNameColumns = [
    { field: "name", label: "Name" },
    { field: "name_type", label: "Name Type" },
    { field: "assigned_or_reported_by", label: "Assigned/Reported By" },
    { field: "assigned_or_reported_date", label: "Assigned/Reported Date" },
    { field: "name_remarks", label: "Remarks" },
];
</script>

<template>
    <DetailsSection
        section-title="2. Identification"
        :visible="true"
    >
        <template #sectionContent>
            <div>
                <h4>2.1 Temporary Numbers</h4>
                <dl v-if="tempNumber">
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

                <StandardDataTable
                    :table-data="newNames || []"
                    :column-definitions="newNameColumns"
                    title="New Site Names"
                />
            </div>
        </template>
    </DetailsSection>
</template>

<style scoped></style>
