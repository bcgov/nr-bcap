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
import type { RemarksAndRestrictedInformationTile } from "@/bcap/schema/ArchaeologySiteSchema.ts";

const props = withDefaults(
    defineProps<{
        data: RemarksAndRestrictedInformationTile | undefined;
        languageCode?: string;
    }>(),
    {
        languageCode: "en",
    },
);

const currentData = computed<RemarksAndRestrictedInformationTile | undefined>(
    (): RemarksAndRestrictedInformationTile | undefined => {
        return props.data?.aliased_data as
            | RemarksAndRestrictedInformationTile
            | undefined;
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
const generalRemarkColumns = [
    { field: "general_remark_date", label: "Date" },
    { field: "general_remark", label: "Remark" },
    { field: "general_remark_source", label: "Source" },
];
const restrictedRemarkColumns = [
    { field: "restricted_remark", label: "Restricted Remarks" },
    { field: "restricted_entry_date", label: "Entered On" },
    { field: "restricted_person", label: "Entered By" },
];
// [ "general_remark_information", "remark_keyword", "contravention_document", "restricted_document", "hca_contravention", "restricted_information_n1", "conviction" ]
</script>

<template>
    <DetailsSection
        section-title="8. Remarks & Restricted Information"
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
                <dl
                    v-if="
                        (currentData?.general_remark_information?.length ?? 0) >
                        0
                    "
                >
                    <dt>General Remarks</dt>
                    <dd>
                        <DataTable
                            :value="currentData?.general_remark_information"
                            data-key="tileid"
                            responsive-layout="scroll"
                            :sort-field="`aliased_data.${generalRemarkColumns[0].field}.display_value`"
                            :sort-order="-1"
                        >
                            <Column
                                v-for="col in generalRemarkColumns"
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
                <dl
                    v-if="
                        (currentData?.restricted_information_n1?.length ?? 0) >
                        0
                    "
                >
                    <dt>Restricted Information</dt>
                    <dd>
                        <DataTable
                            :value="currentData?.restricted_information_n1"
                            data-key="tileid"
                            responsive-layout="scroll"
                            :sort-field="`aliased_data.${restrictedRemarkColumns[1].field}.display_value`"
                            :sort-order="-1"
                        >
                            <Column
                                v-for="col in restrictedRemarkColumns"
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
                    <dt>Restricted Documents</dt>
                    <dd>Need to add files</dd>
                </dl>
            </div>
            <div v-if="currentData?.restricted_information_n1?.length > 0">
                {{
                    Object.keys(
                        currentData.restricted_information_n1[0].aliased_data,
                    )
                }}
            </div>
            <div>{{ currentData }}</div>
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
