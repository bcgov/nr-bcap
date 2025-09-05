<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";
import { getNodeDisplayValue } from "@/bcap/util.ts";

import DataTable from "primevue/datatable";
import Column from "primevue/column";
import StandardDataTable from "@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue";
import "primeicons/primeicons.css";
import type { ArchaeologicalDataTile } from "@/bcap/schema/ArchaeologySiteSchema.ts";

const props = withDefaults(
    defineProps<{
        data: ArchaeologicalDataTile | undefined;
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

// const id_fields = [
//     "borden_number",
//     "registration_date",
//     "registration_status",
//     "parcel_owner_type",
//     "register_type",
//     "site_creation_date",
//     "parent_site",
//     "site_alert",
//     "authority",
//     "site_names",
// ] as const;
// type IdFieldKey = (typeof id_fields)[number];

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
        :visible="true"
    >
        <template #sectionContent>
            <div>
                <StandardDataTable
                    :table-data="currentData?.site_typology"
                    :column-definitions="typologyColumns"
                    title="Site Typology"
                    initial-sort-field="0"
                ></StandardDataTable>
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
