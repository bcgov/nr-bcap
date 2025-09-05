<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";
// main.js or in your component's script setup
import "primeicons/primeicons.css";
import type { RemarksAndRestrictedInformationTile } from "@/bcap/schema/ArchaeologySiteSchema.ts";
import StandardDataTable from "@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue";

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
                <StandardDataTable
                    :table-data="currentData?.general_remark_information"
                    :column-definitions="generalRemarkColumns"
                    :initial-sort-field-index="0"
                    title="General Remarks"
                ></StandardDataTable>
                <StandardDataTable
                    :table-data="currentData?.restricted_information_n1"
                    :column-definitions="restrictedRemarkColumns"
                    :initial-sort-field-index="1"
                ></StandardDataTable>
                <dl>
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
