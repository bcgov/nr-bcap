<script setup lang="ts">
import { computed } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import EmptyState from '@/bcap/components/EmptyState.vue';
import StandardDataTable from '@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue';
import type { SiteVisitSchema } from '@/bcap/schema/SiteVisitSchema.ts';

const props = withDefaults(
    defineProps<{ data: SiteVisitSchema | undefined; loading?: boolean }>(),
    { loading: false },
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

const hasRecommendations = computed(() => {
    return recRows.value && recRows.value.length > 0;
});

const hasRemarks = computed(() => {
    return generalRemarkRows.value && generalRemarkRows.value.length > 0;
});

const recColumns = [
    { field: 'recorders_recommendation', label: "Recorder's Recommendations" },
];

const generalRemarkColumns = [
    { field: 'remark_date', label: 'Date' },
    { field: 'remark', label: 'General Remarks' },
    { field: 'remark_source', label: 'Source' },
    { field: 'entered_on', label: 'Entered On' },
    { field: 'entered_by', label: 'Entered By' },
];
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
                        :table-data="recRows"
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
                        :table-data="generalRemarkRows"
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

<style scoped></style>
