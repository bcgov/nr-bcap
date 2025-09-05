<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";
import { getDisplayValue, getNodeDisplayValue, isEmpty } from "@/bcap/util.ts";
import type {
    AliasedNodeData,
    AliasedTileData,
} from "@/arches_component_lab/types.ts";
// main.js or in your component's script setup
import DataTable from "primevue/datatable";
import Column from "primevue/column";
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
    (): AliasedTileData | undefined => {
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
const typeologyColumns = [
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
                <!--                <dl>-->
                <!--                    <template-->
                <!--                        v-for="field in id_fields"-->
                <!--                        :key="field"-->
                <!--                    >-->
                <!--                        <dt-->
                <!--                            v-if="-->
                <!--                                !isEmpty(-->
                <!--                                    currentData?.[-->
                <!--                                        field as IdFieldKey-->
                <!--                                    ] as AliasedNodeData,-->
                <!--                                )-->
                <!--                            "-->
                <!--                        >-->
                <!--                            {{ labelize(field) }}-->
                <!--                        </dt>-->
                <!--                        <dd-->
                <!--                            v-if="-->
                <!--                                !isEmpty(-->
                <!--                                    currentData?.[-->
                <!--                                        field as IdFieldKey-->
                <!--                                    ] as AliasedNodeData,-->
                <!--                                )-->
                <!--                            "-->
                <!--                        >-->
                <!--                            {{-->
                <!--                                getDisplayValue(-->
                <!--                                    currentData?.[-->
                <!--                                        field as IdFieldKey-->
                <!--                                    ] as AliasedNodeData,-->
                <!--                                )-->
                <!--                            }}-->
                <!--                        </dd>-->
                <!--                    </template>-->
                <!--                </dl>-->
                <dl v-if="(currentData?.site_typology?.length ?? 0) > 0">
                    <dt>Site Typology</dt>
                    <dd>
                        <DataTable
                            :value="currentData?.site_typology"
                            data-key="tileid"
                            responsive-layout="scroll"
                            :sort-field="`aliased_data.${typeologyColumns[3].field}.display_value`"
                            :sort-order="-1"
                        >
                            <Column
                                v-for="col in typeologyColumns"
                                :key="col.field"
                                :header="col.label"
                                :field="`aliased_data.${col.field}.display_value`"
                                sortable
                            >
                                <template #body="slotProps">
                                    {{
                                        getNodeDisplayValue(
                                            slotProps.data,
                                            col.field,
                                        )
                                    }}
                                </template>
                            </Column>
                        </DataTable>
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
