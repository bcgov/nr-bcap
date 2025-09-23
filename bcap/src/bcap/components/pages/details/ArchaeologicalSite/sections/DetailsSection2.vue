<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";
import EmptyState from "@/bcap/components/EmptyState.vue";
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
] as const;

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
    { field: "legal_instrument", label: "Legal Instrument" },
    { field: "act_section", label: "Act/Section" },
    { field: "protection_type", label: "Protection Type" },
    { field: "reference_number", label: "Reference #" },
    { field: "authority_start_date", label: "Start Date" },
    { field: "authority_end_date", label: "Expiry Date" },
    { field: "authority_description", label: "Description" },
    { field: "entered_on", label: "Entered On" },
    { field: "entered_by", label: "Entered By" },
];

const siteNamesColumns = [
    { field: "name", label: "Site Name" },
    { field: "name_type", label: "Site Name Type" },
    { field: "name_remarks", label: "Site Name Remarks" },
    { field: "assigned_or_reported_date", label: "Date Assigned or Reported" },
    { field: "assigned_or_reported_by", label: "Assigned or Reported By" },
    { field: "entered_on", label: "Entered On" },
    { field: "entered_by", label: "Entered By" },
];

type IdFieldKey = (typeof id_fields)[number];

const labelize = (key: string) =>
    key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

const decisionData = computed(() => currentData.value?.site_decision);

const {
    processedData: decisionTableData,
    isProcessing: isProcessingDecisions,
} = useHierarchicalData(decisionData, {
    sourceField: "site_decision",
    hierarchicalFields: ["site_decision", "decision_criteria"],
    flatFields: [
        "decision_date",
        "decision_made_by",
        "decision_description",
        "recommendation_date",
        "recommended_by",
    ],
});

const hasBasicInfo = computed(() => {
    return id_fields.some(
        (field) =>
            !isEmpty(
                currentData.value?.[field as IdFieldKey] as AliasedNodeData,
            ),
    );
});

const hasAdifRecord = computed(() => {
    return currentHriaData.value?.aliased_data?.unreviewed_adif_record
        ?.aliased_data?.unreviewed_adif_record.node_value;
});

const hasAuthority = computed(() => {
    return (
        currentData.value?.authority && currentData.value.authority.length > 0
    );
});

const hasDecisionHistory = computed(() => {
    return decisionTableData.value && decisionTableData.value.length > 0;
});

const hasSiteNames = computed(() => {
    return (
        currentData.value?.site_names && currentData.value.site_names.length > 0
    );
});

const hasCurrentAlerts = computed(() => {
    return !isEmpty(currentData.value?.site_alert as AliasedNodeData);
});

const hasRelatedSites = computed(() => {
    return !isEmpty(currentData.value?.parent_site as AliasedNodeData);
});

const parentSite = computed(() => {
    return currentData.value?.parent_site;
});
</script>

<template>
    <DetailsSection
        section-title="2. ID & Registration"
        :loading="props.loading || isProcessingDecisions"
        :visible="true"
    >
        <template #sectionContent>
            <DetailsSection
                section-title="Basic Information"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasBasicInfo }"
            >
                <template #sectionContent>
                    <div v-if="hasBasicInfo">
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
                    </div>
                    <EmptyState
                        v-else
                        message="No basic identification information available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="ADIF Record Information"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasAdifRecord }"
            >
                <template #sectionContent>
                    <div v-if="hasAdifRecord">
                        <dl>
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
                        </dl>
                    </div>
                    <EmptyState
                        v-else
                        message="No ADIF record information available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Current Alerts"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasCurrentAlerts }"
            >
                <template #sectionContent>
                    <div v-if="hasCurrentAlerts">
                        <dl>
                            <dt>Site Alert</dt>
                            <dd>
                                {{
                                    getDisplayValue(
                                        currentData?.site_alert as AliasedNodeData,
                                    )
                                }}
                            </dd>
                        </dl>
                    </div>
                    <EmptyState
                        v-else
                        message="No current alerts available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Related Sites"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasRelatedSites }"
            >
                <template #sectionContent>
                    <div v-if="hasRelatedSites">
                        <dl>
                            <dt v-if="!isEmpty(parentSite as AliasedNodeData)">
                                Parent Site
                            </dt>
                            <dd v-if="!isEmpty(parentSite as AliasedNodeData)">
                                {{
                                    getDisplayValue(
                                        parentSite as AliasedNodeData,
                                    )
                                }}
                            </dd>
                        </dl>
                    </div>
                    <EmptyState
                        v-else
                        message="No related sites available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Authority"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasAuthority }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasAuthority"
                        :table-data="currentData?.authority ?? []"
                        :column-definitions="authorityColumns"
                        :initial-sort-field-index="3"
                    />
                    <EmptyState
                        v-else
                        message="No authority information available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Decision History"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasDecisionHistory }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasDecisionHistory"
                        :table-data="decisionTableData"
                        :column-definitions="siteDecisionColumns"
                        :initial-sort-field-index="0"
                    />
                    <EmptyState
                        v-else
                        message="No decision history available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Identification"
                variant="subsection"
                :visible="true"
            >
                <template #sectionContent>
                    <DetailsSection
                        section-title="Site Names"
                        variant="subsection"
                        :visible="true"
                        :class="{ 'empty-section': !hasSiteNames }"
                    >
                        <template #sectionContent>
                            <StandardDataTable
                                v-if="hasSiteNames"
                                :table-data="currentData?.site_names ?? []"
                                :column-definitions="siteNamesColumns"
                                :initial-sort-field-index="3"
                            />
                            <EmptyState
                                v-else
                                message="No site names available."
                            />
                        </template>
                    </DetailsSection>
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>
