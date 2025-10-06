<script setup lang="ts">
import { computed, toRef } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import EmptyState from '@/bcap/components/EmptyState.vue';
import { getDisplayValue, isEmpty } from '@/bcap/util.ts';
import { useTileEditLog } from '@/bcgov_arches_common/composables/useTileEditLog.ts';
import type { EditLogData } from '@/bcgov_arches_common/types.ts';
import { EDIT_LOG_FIELDS } from '@/bcgov_arches_common/constants.ts';
import StandardDataTable from '@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue';
import 'primeicons/primeicons.css';
import type { RemarksAndRestrictedInformationTile } from '@/bcap/schema/ArchaeologySiteSchema.ts';
import type { SiteVisitSchema } from '@/bcap/schema/SiteVisitSchema.ts';
import type { ColumnDefinition } from '@/bcgov_arches_common/components/StandardDataTable/types.ts';

const props = withDefaults(
    defineProps<{
        data: RemarksAndRestrictedInformationTile | undefined;
        siteVisitData?: SiteVisitSchema[];
        loading?: boolean;
        languageCode?: string;
        forceCollapsed?: boolean;
        editLogData?: EditLogData;
        showAuditFields?: boolean;
    }>(),
    {
        siteVisitData: () => [],
        loading: false,
        languageCode: 'en',
        forceCollapsed: undefined,
        editLogData: () => ({}),
        showAuditFields: false,
    },
);

const currentData = computed<RemarksAndRestrictedInformationTile | undefined>(
    (): RemarksAndRestrictedInformationTile | undefined => {
        return props.data?.aliased_data as
            | RemarksAndRestrictedInformationTile
            | undefined;
    },
);

const generalRemarkColumns = computed<ColumnDefinition[]>(() => {
    return [
        { field: 'general_remark_date', label: 'Date' },
        { field: 'general_remark', label: 'General Remarks' },
        { field: 'general_remark_source', label: 'Source' },
        {
            field: EDIT_LOG_FIELDS.ENTERED_ON,
            label: 'Entered On',
            visible: props.showAuditFields,
        },
        {
            field: EDIT_LOG_FIELDS.ENTERED_BY,
            label: 'Entered By',
            visible: props.showAuditFields,
        },
    ];
});

const restrictedRemarkColumns = computed<ColumnDefinition[]>(() => {
    return [
        { field: 'restricted_remark', label: 'Restricted Remarks' },
        {
            field: 'restricted_entry_date',
            label: 'Entered On',
            visible: props.showAuditFields,
        },
        {
            field: 'restricted_person',
            label: 'Entered By',
            visible: props.showAuditFields,
        },
    ];
});

const hcaContraventionColumns = computed<ColumnDefinition[]>(() => {
    return [
        { field: 'inventory_remarks', label: 'Inventory Remarks' },
        { field: 'address', label: 'Address' },
        { field: 'pid', label: 'PID' },
        { field: 'nros_file_number', label: 'NROS File #' },
        {
            field: EDIT_LOG_FIELDS.ENTERED_ON,
            label: 'Entered On',
            visible: props.showAuditFields,
        },
        {
            field: EDIT_LOG_FIELDS.ENTERED_BY,
            label: 'Entered By',
            visible: props.showAuditFields,
        },
    ];
});

const convictionColumns = computed<ColumnDefinition[]>(() => {
    return [
        { field: 'conviction_date', label: 'Conviction Date' },
        { field: 'inventory_remarks', label: 'Inventory Remarks' },
        {
            field: EDIT_LOG_FIELDS.ENTERED_ON,
            label: 'Entered On',
            visible: props.showAuditFields,
        },
        {
            field: EDIT_LOG_FIELDS.ENTERED_BY,
            label: 'Entered By',
            visible: props.showAuditFields,
        },
    ];
});

const generalRemarksData = computed(
    () => currentData.value?.general_remark_information || [],
);
const hcaContraventionsData = computed(
    () => currentData.value?.hca_contravention || [],
);
const convictionsData = computed(() => currentData.value?.conviction || []);
const restrictedInfoData = computed(
    () => currentData.value?.restricted_information_n1 || [],
);
const keywordsData = computed(() => {
    const keywords = currentData.value?.remark_keyword;
    if (!keywords) return [];
    return Array.isArray(keywords) ? keywords : [keywords];
});

const { processedData: generalRemarksTableData } = useTileEditLog(
    generalRemarksData,
    toRef(props, 'editLogData'),
);

const { processedData: hcaContraventionsTableData } = useTileEditLog(
    hcaContraventionsData,
    toRef(props, 'editLogData'),
);

const { processedData: convictionsTableData } = useTileEditLog(
    convictionsData,
    toRef(props, 'editLogData'),
);

const hasKeywords = computed(() => keywordsData.value.length > 0);
const hasGeneralRemarks = computed(
    () => generalRemarksTableData.value.length > 0,
);
const hasRestrictedInfo = computed(() => restrictedInfoData.value.length > 0);

const hasDocuments = computed(() => {
    return (
        !isEmpty(currentData.value?.contravention_document) ||
        !isEmpty(currentData.value?.restricted_document)
    );
});

const hasContraventions = computed(
    () => hcaContraventionsTableData.value.length > 0,
);
const hasConvictions = computed(() => convictionsTableData.value.length > 0);
</script>

<template>
    <DetailsSection
        section-title="8. Remarks & Restricted Information"
        :loading="props.loading"
        :visible="true"
        :force-collapsed="props.forceCollapsed"
    >
        <template #sectionContent>
            <DetailsSection
                section-title="Keywords"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasKeywords }"
            >
                <template #sectionContent>
                    <div v-if="hasKeywords">
                        <div
                            v-for="(keyword, index) in keywordsData"
                            :key="index"
                            class="keyword-item"
                        >
                            {{ getDisplayValue(keyword) }}
                        </div>
                    </div>
                    <EmptyState
                        v-else
                        message="No keywords available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="General Remarks"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasGeneralRemarks }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasGeneralRemarks"
                        :table-data="generalRemarksTableData"
                        :column-definitions="generalRemarkColumns"
                        :initial-sort-field-index="0"
                    />
                    <EmptyState
                        v-else
                        message="No general remarks available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Restricted Information"
                variant="subsection"
                :visible="true"
            >
                <template #sectionContent>
                    <DetailsSection
                        section-title="Restricted Remarks"
                        variant="subsection"
                        :visible="true"
                        :class="{ 'empty-section': !hasRestrictedInfo }"
                    >
                        <template #sectionContent>
                            <StandardDataTable
                                v-if="hasRestrictedInfo"
                                :table-data="restrictedInfoData"
                                :column-definitions="restrictedRemarkColumns"
                                :initial-sort-field-index="1"
                            />
                            <EmptyState
                                v-else
                                message="No restricted remarks available."
                            />
                        </template>
                    </DetailsSection>

                    <DetailsSection
                        section-title="Restricted Documents"
                        variant="subsection"
                        :visible="true"
                        :class="{ 'empty-section': !hasDocuments }"
                    >
                        <template #sectionContent>
                            <div v-if="hasDocuments">
                                <dl>
                                    <dt
                                        v-if="
                                            !isEmpty(
                                                currentData?.contravention_document,
                                            )
                                        "
                                    >
                                        Contravention Documents
                                    </dt>
                                    <dd
                                        v-if="
                                            !isEmpty(
                                                currentData?.contravention_document,
                                            )
                                        "
                                    >
                                        {{
                                            getDisplayValue(
                                                currentData?.contravention_document,
                                            )
                                        }}
                                    </dd>

                                    <dt
                                        v-if="
                                            !isEmpty(
                                                currentData?.restricted_document,
                                            )
                                        "
                                    >
                                        Restricted Documents
                                    </dt>
                                    <dd
                                        v-if="
                                            !isEmpty(
                                                currentData?.restricted_document,
                                            )
                                        "
                                    >
                                        {{
                                            getDisplayValue(
                                                currentData?.restricted_document,
                                            )
                                        }}
                                    </dd>
                                </dl>
                            </div>
                            <EmptyState
                                v-else
                                message="No restricted documents available."
                            />
                        </template>
                    </DetailsSection>
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="HCA Contraventions"
                variant="subsection"
                :visible="true"
                :class="{
                    'empty-section': !hasContraventions && !hasConvictions,
                }"
            >
                <template #sectionContent>
                    <DetailsSection
                        section-title="Contraventions"
                        variant="subsection"
                        :visible="true"
                        :class="{ 'empty-section': !hasContraventions }"
                    >
                        <template #sectionContent>
                            <StandardDataTable
                                v-if="hasContraventions"
                                :table-data="hcaContraventionsTableData"
                                :column-definitions="hcaContraventionColumns"
                                :initial-sort-field-index="4"
                            />
                            <EmptyState
                                v-else
                                message="No HCA contraventions available."
                            />
                        </template>
                    </DetailsSection>

                    <DetailsSection
                        section-title="HCA Convictions"
                        variant="subsection"
                        :visible="true"
                        :class="{ 'empty-section': !hasConvictions }"
                    >
                        <template #sectionContent>
                            <StandardDataTable
                                v-if="hasConvictions"
                                :table-data="convictionsTableData"
                                :column-definitions="convictionColumns"
                                :initial-sort-field-index="0"
                            />
                            <EmptyState
                                v-else
                                message="No HCA convictions available."
                            />
                        </template>
                    </DetailsSection>
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>

<style scoped>
dl {
    display: flex;
    flex-direction: column;
    padding-bottom: 1rem;
}
dt {
    min-width: 20rem;
    padding-top: 0.75rem;
    font-weight: 600;
}
dd {
    padding-left: 1rem;
}
.keyword-item {
    padding: 0.25rem 0;
    border-left: 3px solid #007bff;
    padding-left: 0.75rem;
    margin-bottom: 0.5rem;
    background-color: #f8f9fa;
}
</style>
