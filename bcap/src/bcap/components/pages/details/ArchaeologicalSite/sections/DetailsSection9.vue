<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";
// main.js or in your component's script setup
import "primeicons/primeicons.css";

import type { RelatedDocumentsTile } from "@/bcap/schema/ArchaeologySiteSchema.ts";
import StandardDataTable from "@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue";

const props = defineProps<{
    data: RelatedDocumentsTile | undefined;
}>();

const currentData = computed<RelatedDocumentsTile | undefined>(
    (): RelatedDocumentsTile | undefined => {
        return props.data?.aliased_data as RelatedDocumentsTile | undefined;
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
const siteDocumentsColumns = [
    { field: "related_document_type", label: "Type" },
    { field: "related_site_documents", label: "Document" },
    { field: "related_document_description", label: "Description" },
];

// [ "general_remark_information", "remark_keyword", "contravention_document", "restricted_document", "hca_contravention", "restricted_information_n1", "conviction" ]
</script>

<template>
    <DetailsSection
        section-title="9. References & Related Documents"
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
                <dl>
                    <dt>References</dt>
                    <dd>Need to add references</dd>
                    <dt>Related Documents</dt>
                    <dd>Need to add related documents</dd>
                    <dt>Images</dt>
                    <dd>Need to add images</dd>
                    <dt>Other Maps</dt>
                    <dd>Need to add other maps?</dd>
                </dl>
                <StandardDataTable
                    :table-data="currentData?.related_site_documents ?? []"
                    :column-definitions="siteDocumentsColumns"
                    :initial-sort-field-index="0"
                    title="Site Documents"
                ></StandardDataTable>
                <dl>
                    <dt>Restricted Documents</dt>
                    <dd>Need to add files</dd>
                </dl>
            </div>
            <pre>
                {{ currentData }}
            </pre>
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
