<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";
import { getDisplayValue, isEmpty } from "@/bcap/util.ts";
import { useHierarchicalData } from "@/bcap/composables/useHierarchicalData.ts";
import type {
    AliasedNodeData,
    AliasedTileData,
} from "@/arches_component_lab/types.ts";
import StandardDataTable from "@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue";
import "primeicons/primeicons.css";
import type { IdentificationAndRegistrationTile } from "@/bcap/schema/ArchaeologySiteSchema.ts";
import type { HriaDiscontinuedDataSchema } from "@/bcap/schema/HriaDiscontinuedDataSchema.ts";

const props = withDefaults(
    defineProps<{
        data: IdentificationAndRegistrationTile | undefined;
        hriaData: HriaDiscontinuedDataSchema | undefined;
        loading?: boolean;
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

const currentHriaData = computed<HriaDiscontinuedDataSchema | undefined>(
    (): HriaDiscontinuedDataSchema | undefined => {
        return props.hriaData as HriaDiscontinuedDataSchema | undefined;
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

const decisionData = computed(() => currentData.value?.site_decision);

const { processedData: decisionTableData, isProcessing: isProcessingDecisions } = useHierarchicalData(
    decisionData,
    {
        sourceField: 'site_decision',
        hierarchicalFields: ['site_decision', 'decision_criteria'],
        flatFields: ['decision_date', 'decision_made_by', 'decision_description', 'recommendation_date', 'recommended_by']
    }
);
</script>

<template>
    <DetailsSection
        section-title="2. ID & Registration"
        :loading="props.loading || isProcessingDecisions"
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
                    <div
                        v-if="
                            currentHriaData?.aliased_data
                                ?.unreviewed_adif_record?.aliased_data
                                ?.unreviewed_adif_record.node_value
                        "
                    >
                        <dt>Is ADIF Record?</dt>
                        <dd>Yes</dd>
                        <dt>Site Entered By / Date:</dt>
                        <dd>
                            {{
                                currentHriaData?.aliased_data
                                    ?.unreviewed_adif_record?.aliased_data
                                    ?.site_entered_by?.display_value
                            }}
                            /
                            {{
                                currentHriaData?.aliased_data
                                    ?.unreviewed_adif_record?.aliased_data
                                    ?.site_entry_date?.display_value
                            }}
                        </dd>
                    </div>
                </dl>
                <StandardDataTable
                    :table-data="currentData?.authority ?? []"
                    :column-definitions="authorityColumns"
                    title="Authority"
                    :initial-sort-field-index="3"
                ></StandardDataTable>
                <StandardDataTable
                    :table-data="decisionTableData"
                    :column-definitions="siteDecisionColumns"
                    title="Decision History"
                    :initial-sort-field-index="0"
                ></StandardDataTable>
            </div>
        </template>
    </DetailsSection>
</template>
