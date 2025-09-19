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

const remainsRows = computed(
    () => props.data?.aliased_data?.ancestral_remains || [],
);

const hasRemains = computed(() => {
    return remainsRows.value && remainsRows.value.length > 0;
});

const remainsColumns = [
    { field: "ancestral_remains_type", label: "Type" },
    { field: "ancestral_remains_status", label: "Status" },
    { field: "ancestral_remains_remarks", label: "Remarks" },
    { field: "multiple_burials", label: "Multiple Burials" },
    { field: "minimum_number_of_individuals", label: "Minimum # Individuals" },
    { field: "ancestral_remains_repository", label: "Repository" },
];
</script>

<template>
    <DetailsSection
        section-title="5. Ancestral Remains"
        :visible="true"
        :loading="props.loading"
    >
        <template #sectionContent>
            <DetailsSection
                section-title="Ancestral Remains Data"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasRemains }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasRemains"
                        :table-data="remainsRows"
                        :column-definitions="remainsColumns"
                    />
                    <EmptyState
                        v-else
                        message="No ancestral remains information available."
                    />
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>

<style scoped></style>
