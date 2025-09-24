<script setup lang="ts">
import { computed } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';

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
const recColumns = [
    { field: 'recorders_recommendation', label: 'Recommendation' },
];
const remarkRows = computed(
    () =>
        props.data?.aliased_data?.remarks_and_recommendations?.aliased_data
            ?.general_remark || [],
);
const remarkColumns = [
    { field: 'remark_source', label: 'Source' },
    { field: 'remark_date', label: 'Date' },
    { field: 'remark', label: 'Remark' },
];
</script>

<template>
    <DetailsSection
        section-title="6. Remarks and Recommendations"
        :visible="true"
        :loading="props.loading"
    >
        <template #sectionContent>
            <h4>6.1 Recommendations</h4>
            <StandardDataTable
                :table-data="recRows"
                :column-definitions="recColumns"
            />
            <h4>6.2 General Remarks</h4>
            <StandardDataTable
                :table-data="remarkRows"
                :column-definitions="remarkColumns"
            />
        </template>
    </DetailsSection>
</template>

<style scoped></style>
