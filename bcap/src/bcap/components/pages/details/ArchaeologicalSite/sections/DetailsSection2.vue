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
import type { IdentificationAndRegistrationTile } from "@/bcap/schema/ArchaeologySiteSchema.ts";

const props = withDefaults(
    defineProps<{
        data: IdentificationAndRegistrationTile | undefined;
        languageCode?: string;
    }>(),
    {
        languageCode: "en",
    },
);

const currentData = computed<IdentificationAndRegistrationTile | undefined>(
    (): AliasedTileData | undefined => {
        return props.data?.aliased_data as
            | IdentificationAndRegistrationTile
            | undefined;
    },
);

const id_fields = [
    "borden_number",
    "registration_date",
    "registration_status",
    "parcel_owner_type",
    "register_type",
    "site_creation_date",
    "parent_site",
    "site_alert",
    "authority",
    "site_names",
] as const;

/** Generic column definitions: configure any key/path + label */
const siteDecisionColumns = [
    { field: "decision_date", label: "Decision Date" },
    { field: "decision_made_by", label: "Decision Maker" },
    { field: "site_decision", label: "Decision" },
    { field: "decision_criteria", label: "Criteria" },
    { field: "decision_description", label: "Description" },
    { field: "recommendation_date", label: "Recommended On" },
    { field: "recommended_by", label: "Recommended By" },
];

const authorityColumns = [
    { field: "responsible_government", label: "Government" },
    { field: "legislative_act", label: "Legislative Act" },
    { field: "reference_number", label: "Reference #" },
    { field: "authority_start_date", label: "Start Date" },
    { field: "authority_end_date", label: "End Date" },
    { field: "authority_description", label: "Description" },
];

type IdFieldKey = (typeof id_fields)[number];

// Turn "borden_number" -> "Borden Number"
const labelize = (key: string) =>
    key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
</script>

<template>
    <DetailsSection
        section-title="2. ID & Registration"
        :visible="true"
    >
        <template #sectionContent>
            <div>
                <dl>
                    <template
                        v-for="field in id_fields"
                        :key="field"
                    >
                        <dt
                            v-if="
                                !isEmpty(
                                    currentData?.[
                                        field as IdFieldKey
                                    ] as AliasedNodeData,
                                )
                            "
                        >
                            {{ labelize(field) }}
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    currentData?.[
                                        field as IdFieldKey
                                    ] as AliasedNodeData,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    currentData?.[
                                        field as IdFieldKey
                                    ] as AliasedNodeData,
                                )
                            }}
                        </dd>
                    </template>
                </dl>
                <dl v-if="(currentData?.authority?.length ?? 0) > 0">
                    <dt>Authority</dt>
                    <dd>
                        <DataTable
                            :value="currentData?.authority"
                            data-key="tileid"
                            responsive-layout="scroll"
                            :sort-field="`aliased_data.${authorityColumns[3].field}.display_value`"
                            :sort-order="-1"
                        >
                            <Column
                                v-for="col in authorityColumns"
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
                <dl v-if="(currentData?.site_decision?.length ?? 0) > 0">
                    <dt>Decision History</dt>
                    <dd>
                        <DataTable
                            :value="currentData?.site_decision"
                            data-key="tileid"
                            responsive-layout="scroll"
                            :sort-field="`aliased_data.${siteDecisionColumns[0].field}.display_value`"
                            :sort-order="-1"
                        >
                            <Column
                                v-for="col in siteDecisionColumns"
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
            <div>HI!{{ Object.keys(currentData) }}</div>
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
