<script setup lang="ts">
import { computed, toRef } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import EmptyState from '@/bcap/components/EmptyState.vue';
import { useHierarchicalData } from '@/bcap/composables/useHierarchicalData.ts';
import { useTileEditLog } from '@/bcgov_arches_common/composables/useTileEditLog.ts';
import type { EditLogData } from '@/bcgov_arches_common/types.ts';
import { EDIT_LOG_FIELDS } from '@/bcgov_arches_common/constants.ts';
import StandardDataTable from '@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue';
import 'primeicons/primeicons.css';
import type { ArchaeologicalDataTile } from '@/bcap/schema/ArchaeologySiteSchema.ts';

const props = withDefaults(
    defineProps<{
        data: ArchaeologicalDataTile | undefined;
        loading?: boolean;
        languageCode?: string;
        forceCollapsed?: boolean;
        editLogData?: EditLogData;
    }>(),
    {
        languageCode: 'en',
        forceCollapsed: undefined,
        editLogData: () => ({}),
    },
);

const currentData = computed<ArchaeologicalDataTile | undefined>(
    (): ArchaeologicalDataTile | undefined => {
        return props.data?.aliased_data as ArchaeologicalDataTile | undefined;
    },
);

const typologyColumns = [
    { field: 'typology_class', label: 'Class' },
    { field: 'site_type', label: 'Type' },
    { field: 'site_subtype', label: 'Subtype' },
    { field: 'typology_descriptor', label: 'Descriptor' },
];

const typologyRemarksColumns = [
    { field: 'site_typology_remarks', label: 'Site Typology Remarks' },
    { field: EDIT_LOG_FIELDS.ENTERED_ON, label: 'Entered On' },
    { field: EDIT_LOG_FIELDS.ENTERED_BY, label: 'Entered By' },
];

const typologyData = computed(() => currentData.value?.site_typology);

const { processedData: typologyTableData, isProcessing } = useHierarchicalData(
    typologyData,
    {
        sourceField: 'typology_class',
        hierarchicalFields: [
            'typology_class',
            'site_type',
            'site_subtype',
            'typology_descriptor',
        ],
    },
);

const typologyRemarksData = computed(
    () => currentData.value?.site_typology_remarks || [],
);

const { processedData: typologyRemarksTableData } = useTileEditLog(
    typologyRemarksData,
    toRef(props, 'editLogData'),
);

const hasTypology = computed(() => {
    return typologyTableData.value && typologyTableData.value.length > 0;
});

const hasTypologyRemarks = computed(() => {
    return (
        typologyRemarksTableData.value &&
        typologyRemarksTableData.value.length > 0
    );
});
</script>

<template>
    <DetailsSection
        section-title="6. Archaeological Data"
        :loading="props.loading || isProcessing"
        :visible="true"
        :force-collapsed="props.forceCollapsed"
    >
        <template #sectionContent>
            <DetailsSection
                section-title="Site Typology"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasTypology }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasTypology"
                        :table-data="typologyTableData"
                        :column-definitions="typologyColumns"
                        :initial-sort-field-index="0"
                    />
                    <EmptyState
                        v-else
                        message="No site typology information available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Site Typology Remarks"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasTypologyRemarks }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasTypologyRemarks"
                        :table-data="typologyRemarksTableData"
                        :column-definitions="typologyRemarksColumns"
                        :initial-sort-field-index="1"
                    />
                    <EmptyState
                        v-else
                        message="No site typology remarks available."
                    />
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>
