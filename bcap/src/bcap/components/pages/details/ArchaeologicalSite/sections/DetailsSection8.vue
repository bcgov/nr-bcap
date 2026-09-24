<script setup lang="ts">
import { computed, toRef, type Ref } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import EmptyState from '@/bcap/components/EmptyState.vue';
import { getDisplayValue } from '@/bcap/util.ts';
import { useTileEditLog } from '@/bcgov_arches_common/composables/useTileEditLog.ts';
import type { EditLogData } from '@/bcgov_arches_common/types.ts';
import { EDIT_LOG_FIELDS } from '@/bcgov_arches_common/constants.ts';
import StandardDataTable from '@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue';
import 'primeicons/primeicons.css';
import type {
    AliasedNodeData,
    AliasedTileData,
} from '@/arches_vue_components/types.ts';
import type {
    ArchaeologicalSiteRemarksAndRestrictedInformationTile,
    ArchaeologicalSiteRemarksAndRestrictedInformationAliasedData,
    ArchaeologicalSiteGeneralRemarkInformationTile,
    SiteVisit,
    SiteVisitGeneralRemarkTile,
} from '@/bcap/client/types.gen.ts';
import type { ColumnDefinition } from '@/bcgov_arches_common/components/StandardDataTable/types.ts';
import { formatFilenameUrl } from '@/bcgov_arches_common/datatypes/file-list/utils.ts';
import {
    applyFileLinks,
    expandDocumentRows,
} from '@/bcgov_arches_common/utils/document.ts';

const props = withDefaults(
    defineProps<{
        data: ArchaeologicalSiteRemarksAndRestrictedInformationTile | undefined;
        siteVisitData?: SiteVisit[];
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

const currentData = computed<
    ArchaeologicalSiteRemarksAndRestrictedInformationAliasedData | undefined
>(
    ():
        | ArchaeologicalSiteRemarksAndRestrictedInformationAliasedData
        | undefined => {
        return props.data?.aliased_data;
    },
);

const generalRemarkColumns = computed<ColumnDefinition[]>(() => {
    return [
        { field: 'general_remark_date', label: 'Date' },
        { field: 'general_remark', label: 'General Remarks', isHtml: true },
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
        {
            field: 'restricted_remark',
            label: 'Restricted Remarks',
            isHtml: true,
        },
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

const contraventionDocumentColumns = computed<ColumnDefinition[]>(() => {
    return [
        {
            field: 'contravention_document',
            label: 'Document',
            isHtml: true,
            displayFunction: formatFilenameUrl,
        },
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

const restrictedDocumentColumns = computed<ColumnDefinition[]>(() => {
    return [
        {
            field: 'restricted_document',
            label: 'Document',
            isHtml: true,
            displayFunction: formatFilenameUrl,
        },
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

const hcaContraventionColumns = computed<ColumnDefinition[]>(() => {
    return [
        { field: 'inventory_remark', label: 'Inventory Remarks', isHtml: true },
        { field: 'contravention_address', label: 'Address' },
        { field: 'contravention_pid', label: 'PID' },
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
        {
            field: 'conviction_details',
            label: 'Inventory Remarks',
            isHtml: true,
        },
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

const toArchSiteRemark = (
    tile: SiteVisitGeneralRemarkTile,
): ArchaeologicalSiteGeneralRemarkInformationTile => ({
    ...tile,
    aliased_data: {
        general_remark_source: tile.aliased_data?.remark_source ?? null,
        general_remark_date: tile.aliased_data?.remark_date ?? null,
        general_remark: tile.aliased_data?.remark ?? null,
    },
});

const remarksFromSiteVisit = (
    sv: SiteVisit,
): ArchaeologicalSiteGeneralRemarkInformationTile[] =>
    sv.aliased_data?.remarks_and_recommendations?.aliased_data?.general_remark?.map(
        toArchSiteRemark,
    ) ?? [];

const generalRemarksData = computed<
    ArchaeologicalSiteGeneralRemarkInformationTile[]
>(() => [
    ...(currentData.value?.general_remark_information ?? []),
    ...props.siteVisitData.flatMap(remarksFromSiteVisit),
]);
const hcaContraventionsData = computed(
    () => currentData.value?.hca_contravention || [],
);
const convictionsData = computed(() => currentData.value?.conviction || []);
const restrictedInfoDataRaw = computed(
    () => currentData.value?.restricted_information || [],
);
const keywordsData = computed(() => {
    const keywords = currentData.value?.remark_keyword;
    if (!keywords) return [];
    const keywordsArray = Array.isArray(keywords) ? keywords : [keywords];
    return keywordsArray
        .map((tile) => tile.aliased_data?.remark_keyword)
        .filter(
            (keyword): keyword is NonNullable<typeof keyword> => !!keyword,
        ) as unknown as AliasedNodeData[];
});

const contraventionDocumentsExpanded = computed(() => {
    const docs = currentData.value?.contravention_document;
    if (!docs) return [];
    const docsArray = Array.isArray(docs) ? docs : [docs];
    return expandDocumentRows(
        docsArray as unknown as AliasedTileData[],
        'contravention_document',
    );
});

const restrictedDocumentsExpanded = computed(() => {
    const docs = currentData.value?.restricted_document;
    if (!docs) return [];
    const docsArray = Array.isArray(docs) ? docs : [docs];
    return expandDocumentRows(
        docsArray as unknown as AliasedTileData[],
        'restricted_document',
    );
});

const { processedData: generalRemarksTableData } = useTileEditLog(
    generalRemarksData as Ref<AliasedTileData[]>,
    toRef(props, 'editLogData'),
);

const { processedData: hcaContraventionsTableData } = useTileEditLog(
    hcaContraventionsData as Ref<AliasedTileData[]>,
    toRef(props, 'editLogData'),
);

const { processedData: convictionsTableData } = useTileEditLog(
    convictionsData as Ref<AliasedTileData[]>,
    toRef(props, 'editLogData'),
);

const { processedData: restrictedInfoData } = useTileEditLog(
    restrictedInfoDataRaw as Ref<AliasedTileData[]>,
    toRef(props, 'editLogData'),
);

const { processedData: contraventionDocumentsProcessed } = useTileEditLog(
    contraventionDocumentsExpanded as Ref<AliasedTileData[]>,
    toRef(props, 'editLogData'),
);

const { processedData: restrictedDocumentsProcessed } = useTileEditLog(
    restrictedDocumentsExpanded as Ref<AliasedTileData[]>,
    toRef(props, 'editLogData'),
);

const contraventionDocumentsTableData = computed(() =>
    applyFileLinks(
        contraventionDocumentsProcessed.value,
        'contravention_document',
    ),
);

const restrictedDocumentsTableData = computed(() =>
    applyFileLinks(restrictedDocumentsProcessed.value, 'restricted_document'),
);

const hasKeywords = computed(() => keywordsData.value.length > 0);
const hasGeneralRemarks = computed(
    () => generalRemarksTableData.value.length > 0,
);
const hasRestrictedInfo = computed(() => restrictedInfoData.value.length > 0);

const hasContraventionDocuments = computed(
    () => contraventionDocumentsTableData.value.length > 0,
);
const hasRestrictedDocuments = computed(
    () => restrictedDocumentsTableData.value.length > 0,
);

const hasContraventions = computed(
    () => hcaContraventionsTableData.value.length > 0,
);
const hasConvictions = computed(() => convictionsTableData.value.length > 0);

const hasHcaContraventionsSection = computed(
    () =>
        hasContraventions.value ||
        hasContraventionDocuments.value ||
        hasConvictions.value,
);
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
                        :class="{ 'empty-section': !hasRestrictedDocuments }"
                    >
                        <template #sectionContent>
                            <StandardDataTable
                                v-if="hasRestrictedDocuments"
                                :table-data="restrictedDocumentsTableData"
                                :column-definitions="restrictedDocumentColumns"
                            />
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
                    'empty-section': !hasHcaContraventionsSection,
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
                        section-title="Contravention Documents"
                        variant="subsection"
                        :visible="true"
                        :class="{
                            'empty-section': !hasContraventionDocuments,
                        }"
                    >
                        <template #sectionContent>
                            <StandardDataTable
                                v-if="hasContraventionDocuments"
                                :table-data="contraventionDocumentsTableData"
                                :column-definitions="
                                    contraventionDocumentColumns
                                "
                            />
                            <EmptyState
                                v-else
                                message="No contravention documents available."
                            />
                        </template>
                    </DetailsSection>

                    <DetailsSection
                        section-title="Convictions"
                        variant="subsection"
                        :visible="true"
                        :class="{ 'empty-section': !hasConvictions }"
                    >
                        <template #sectionContent>
                            <StandardDataTable
                                v-if="hasConvictions"
                                :table-data="convictionsTableData"
                                :column-definitions="convictionColumns"
                            />
                            <EmptyState
                                v-else
                                message="No convictions available."
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
