<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";

import StandardDataTable from "@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue";
import type { SiteVisitSchema } from "@/bcap/schema/SiteVisitSchema.ts";

const props = withDefaults(
    defineProps<{ data: SiteVisitSchema | undefined; loading?: boolean }>(),
    { loading: false },
);
const remainsRows = computed(
    () => props.data?.aliased_data?.ancestral_remains || [],
);
const remainsColumns = [
    { field: "ancestral_remains_type", label: "Type" },
    { field: "multiple_burials", label: "Multiple Burials" },
    { field: "ancestral_remains_status", label: "Status" },
    { field: "ancestral_remains_remarks", label: "Remarks" },
    { field: "minimum_number_of_individuals", label: "Min # Individuals" },
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
            <StandardDataTable
                :table-data="remainsRows"
                :column-definitions="remainsColumns"
            />
        </template>
    </DetailsSection>
</template>

<style scoped></style>
