<script setup lang="ts">
import { computed, toRef } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import EmptyState from '@/bcap/components/EmptyState.vue';
import StandardDataTable from '@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue';
import { useTileEditLog } from '@/bcgov_arches_common/composables/useTileEditLog.ts';
import type { EditLogData } from '@/bcgov_arches_common/types.ts';
import { EDIT_LOG_FIELDS } from '@/bcgov_arches_common/constants.ts';
import type { SiteVisitSchema } from '@/bcap/schema/SiteVisitSchema.ts';

const props = withDefaults(
    defineProps<{
        data: SiteVisitSchema | undefined;
        loading?: boolean;
        editLogData?: EditLogData;
    }>(),
    {
        loading: false,
        editLogData: () => ({}),
    },
);

const recRows = computed(
    () =>
        props.data?.aliased_data?.remarks_and_recommendations?.aliased_data
            ?.recommendation || [],
);
const generalRemarkRows = computed(
    () =>
        props.data?.aliased_data?.remarks_and_recommendations?.aliased_data
            ?.general_remark || [],
);

const recColumns = [
    { field: 'recorders_recommendation', label: "Recorder's Recommendations" },
    { field: EDIT_LOG_FIELDS.ENTERED_ON, label: 'Entered On' },
    { field: EDIT_LOG_FIELDS.ENTERED_BY, label: 'Entered By' },
];

const generalRemarkColumns = [
    { field: 'remark_date', label: 'Date' },
    { field: 'remark', label: 'General Remarks' },
    { field: 'remark_source', label: 'Source' },
    { field: EDIT_LOG_FIELDS.ENTERED_ON, label: 'Entered On' },
    { field: EDIT_LOG_FIELDS.ENTERED_BY, label: 'Entered By' },
];

const { processedData: recommendationsTableData } = useTileEditLog(
    recRows,
    toRef(props, 'editLogData'),
);

const { processedData: generalRemarksTableData } = useTileEditLog(
    generalRemarkRows,
    toRef(props, 'editLogData'),
);

const hasRecommendations = computed(() => {
    return (
        recommendationsTableData.value &&
        recommendationsTableData.value.length > 0
    );
});

const hasRemarks = computed(() => {
    return (
        generalRemarksTableData.value &&
        generalRemarksTableData.value.length > 0
    );
});
</script>

<template>
    <DetailsSection
        section-title="6. Remarks and Recommendations"
        :visible="true"
        :loading="props.loading"
    >
        <template #sectionContent>
            <DetailsSection
                section-title="Recommendations"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasRecommendations }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasRecommendations"
                        :table-data="recommendationsTableData"
                        :column-definitions="recColumns"
                    />
                    <EmptyState
                        v-else
                        message="No recommendations available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="General Remarks"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasRemarks }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasRemarks"
                        :table-data="generalRemarksTableData"
                        :column-definitions="generalRemarkColumns"
                    />
                    <EmptyState
                        v-else
                        message="No general remarks available."
                    />
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>
