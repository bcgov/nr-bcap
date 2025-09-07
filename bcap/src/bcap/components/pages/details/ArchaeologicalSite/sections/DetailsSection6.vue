<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";

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

/** Generic column definitions: configure any key/path + label */
const typologyColumns = [
    { field: "typology_class", label: "Class" },
    { field: "site_type", label: "Type" },
    { field: "site_subtype", label: "Subtype" },
    { field: "typology_descriptor", label: "Descriptor" },
    { field: "typology_remark", label: "Remarks" },
];
</script>

<template>
    <DetailsSection
        section-title="6. Archaeological Data"
        :loading="props.loading"
        :visible="true"
    >
        <template #sectionContent>
            <div>
                <StandardDataTable
                    :table-data="currentData?.site_typology ?? []"
                    :column-definitions="typologyColumns"
                    title="Site Typology"
                    initial-sort-field="0"
                ></StandardDataTable>
            </div>
        </template>
    </DetailsSection>
</template>
