<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";

import StandardDataTable from "@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue";
import type { SiteVisitSchema } from "@/bcap/schema/SiteVisitSchema.ts";

const props = withDefaults(
    defineProps<{ data: SiteVisitSchema | undefined; loading?: boolean }>(),
    { loading: false },
);
const arch = computed(() => props.data?.aliased_data?.archaeological_data);

const cultureRows = computed(
    () => arch.value?.aliased_data?.archaeological_culture || [],
);
const cultureColumns = [
    { field: "archaeological_culture", label: "Culture" },
    { field: "culture_remarks", label: "Remarks" },
];

const featureRows = computed(
    () => arch.value?.aliased_data?.archaeological_feature || [],
);
const featureColumns = [
    { field: "archaeological_feature", label: "Feature" },
    { field: "feature_count", label: "Count" },
    { field: "feature_remarks", label: "Remarks" },
];

const materialRows = computed(
    () => arch.value?.aliased_data?.cultural_material || [],
);
const materialColumns = [
    { field: "cultural_material_type", label: "Type" },
    { field: "cultural_material_status", label: "Status" },
    { field: "cultural_material_details", label: "Details" },
    { field: "number_of_artifacts", label: "Artifacts" },
    { field: "repository", label: "Repository" },
];

const stratRows = computed(() => arch.value?.aliased_data?.stratigraphy || []);
const stratColumns = [{ field: "stratigraphy", label: "Stratigraphy" }];

const disturbRows = computed(
    () => arch.value?.aliased_data?.site_disturbance || [],
);

const disturbColumns = [
    { field: "disturbance_period", label: "Period" },
    { field: "disturbance_cause", label: "Cause" },
    { field: "disturbance_remarks", label: "Remarks" },
];
</script>

<template>
    <DetailsSection
        section-title="4. Archaeological Data"
        :visible="true"
        :loading="props.loading"
    >
        <template #sectionContent>
            <div>
                <StandardDataTable
                    :table-data="cultureRows"
                    :column-definitions="cultureColumns"
                    title="Archaeological Culture"
                />

                <StandardDataTable
                    :table-data="featureRows"
                    :column-definitions="featureColumns"
                    title="Archaeological Features"
                />

                <StandardDataTable
                    :table-data="materialRows"
                    :column-definitions="materialColumns"
                    title="Cultural Material"
                />

                <StandardDataTable
                    :table-data="stratRows"
                    :column-definitions="stratColumns"
                    title="Stratigraphy"
                />

                <StandardDataTable
                    :table-data="disturbRows"
                    :column-definitions="disturbColumns"
                    title="Site Disturbance"
                />
            </div>
        </template>
    </DetailsSection>
</template>

<style scoped></style>
