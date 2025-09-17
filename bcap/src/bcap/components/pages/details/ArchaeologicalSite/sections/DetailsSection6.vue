<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";
import { useHierarchicalData } from "@/bcap/composables/useHierarchicalData.ts";
import StandardDataTable from "@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue";
import "primeicons/primeicons.css";
import type { ArchaeologicalDataTile } from "@/bcap/schema/ArchaeologySiteSchema.ts";

const props = withDefaults(
    defineProps<{
        data: ArchaeologicalDataTile | undefined;
        loading?: boolean;
        languageCode?: string;
    }>(),
    {
        languageCode: "en",
    },
);

const currentData = computed<ArchaeologicalDataTile | undefined>(
    (): ArchaeologicalDataTile | undefined => {
        return props.data?.aliased_data as ArchaeologicalDataTile | undefined;
    },
);

const typologyColumns = [
    { field: "typology_class", label: "Class" },
    { field: "site_type", label: "Type" },
    { field: "site_subtype", label: "Subtype" },
    { field: "typology_descriptor", label: "Descriptor" },
    { field: "typology_remark", label: "Remarks" },
];

const typologyData = computed(() => currentData.value?.site_typology);

const { processedData: typologyTableData, isProcessing } = useHierarchicalData(
    typologyData,
    {
        sourceField: 'typology_class',
        hierarchyFields: ['typology_class', 'site_type', 'site_subtype', 'typology_descriptor'],
        otherFields: ['typology_remark']
    }
);
</script>

<template>
    <DetailsSection
        section-title="6. Archaeological Data"
        :loading="props.loading || isProcessing"
        :visible="true"
    >
        <template #sectionContent>
            <StandardDataTable
                :table-data="typologyTableData"
                :column-definitions="typologyColumns"
                title="Site Typology"
                :initial-sort-field-index="0"
            />
        </template>
    </DetailsSection>
</template>
