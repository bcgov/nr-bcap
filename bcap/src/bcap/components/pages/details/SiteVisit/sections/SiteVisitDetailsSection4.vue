<script setup lang="ts">
import { computed } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import EmptyState from '@/bcap/components/EmptyState.vue';
import StandardDataTable from '@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue';
import type { SiteVisitSchema } from '@/bcap/schema/SiteVisitSchema.ts';
import type { HriaDiscontinuedDataSchema } from '@/bcap/schema/HriaDiscontinuedDataSchema.ts';

const props = withDefaults(
    defineProps<{
        data: SiteVisitSchema | undefined;
        hriaData: HriaDiscontinuedDataSchema | undefined;
        loading?: boolean;
    }>(),
    { loading: false },
);

const arch = computed(() => props.data?.aliased_data?.archaeological_data);

const cultureRows = computed(
    () => arch.value?.aliased_data?.archaeological_culture || [],
);
const featureRows = computed(
    () => arch.value?.aliased_data?.archaeological_feature || [],
);
const materialRows = computed(
    () => arch.value?.aliased_data?.cultural_material || [],
);
const stratRows = computed(() => arch.value?.aliased_data?.stratigraphy || []);
const chronologyRows = computed(
    () => arch.value?.aliased_data?.chronology || [],
);
const hriaChronologyRows = computed(
    () => props.hriaData?.aliased_data?.chronology || [],
);
const disturbRows = computed(
    () => arch.value?.aliased_data?.site_disturbance || [],
);

const hasFeatures = computed(() => featureRows.value.length > 0);
const hasMaterial = computed(() => materialRows.value.length > 0);
const hasStratigraphy = computed(() => stratRows.value.length > 0);
const hasCulture = computed(() => cultureRows.value.length > 0);
const hasChronology = computed(() => chronologyRows.value.length > 0);
const hasHriaChronology = computed(() => hriaChronologyRows.value.length > 0);
const hasDisturbance = computed(() => disturbRows.value.length > 0);

const cultureColumns = [
    { field: 'archaeological_culture', label: 'Archaeological Culture Name' },
    { field: 'culture_remarks', label: 'Remarks', isHtml: true },
];

const featureColumns = [
    { field: 'archaeological_feature', label: 'Feature Type' },
    { field: 'feature_count', label: '# of Features' },
    { field: 'feature_remarks', label: 'Feature Remarks', isHtml: true },
];

const materialColumns = [
    { field: 'cultural_material_type', label: 'Material Type' },
    { field: 'cultural_material_status', label: 'Status' },
    { field: 'cultural_material_details', label: 'Details', isHtml: true },
    { field: 'number_of_artifacts', label: '# of Artifacts' },
    { field: 'repository', label: 'Repository' },
];

const stratColumns = [{ field: 'stratigraphy', label: 'Stratigraphy', isHtml: true }];

const chronologyColumns = [
    { field: 'determination_method', label: 'Method' },
    { field: 'information_source', label: 'Source' },
    { field: 'chronology_remarks', label: 'Chronology Remarks' },
    { field: 'start_year', label: 'From Date' },
    { field: 'start_year_qualifier', label: 'From Date Qualifier' },
    { field: 'start_year_calendar', label: 'From Date Calendar' },
    { field: 'end_year', label: 'To Date' },
    { field: 'end_year_qualifier', label: 'To Date Qualifier' },
    { field: 'end_year_calendar', label: 'To Date Calendar' },
];

const hriaChronologyColumns = [
    { field: 'determination_method', label: 'Method' },
    { field: 'information_source', label: 'Source' },
    { field: 'chronology_remarks', label: 'Chronology Remarks' },
    { field: 'start_year', label: 'From Date' },
    { field: 'start_year_qualifier', label: 'From Date Qualifier' },
    { field: 'start_year_calendar', label: 'From Date Calendar' },
    { field: 'end_year', label: 'To Date' },
    { field: 'end_year_qualifier', label: 'To Date Qualifier' },
    { field: 'end_year_calendar', label: 'To Date Calendar' },
    { field: 'rcd_unadjusted', label: 'RCD Unadjusted' },
    { field: 'rcd_unadjusted_var', label: 'RCD Unadjusted Var (+/-)' },
    { field: 'rcd_adjusted', label: 'RCD Adjusted' },
    { field: 'rcd_adjusted_var', label: 'RCD Adjusted Var (+/-)' },
    { field: 'rcd_lab_code', label: 'RCD Lab Code' },
    { field: 'rcd_lab_number', label: 'RCD Lab Number' },
    { field: 'modified_on', label: 'Modified On' },
    { field: 'modified_by', label: 'Modified By' },
];

const disturbColumns = [
    { field: 'disturbance_period', label: 'When' },
    { field: 'disturbance_cause', label: 'Cause of Disturbance' },
    { field: 'disturbance_remarks', label: 'Disturbance Remarks', isHtml: true },
];
</script>

<template>
    <DetailsSection
        section-title="4. Archaeological Data"
        :visible="true"
        :loading="props.loading"
    >
        <template #sectionContent>
            <DetailsSection
                section-title="Archaeological Features"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasFeatures }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasFeatures"
                        :table-data="featureRows"
                        :column-definitions="featureColumns"
                    />
                    <EmptyState
                        v-else
                        message="No archaeological features available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Cultural Material"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasMaterial }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasMaterial"
                        :table-data="materialRows"
                        :column-definitions="materialColumns"
                    />
                    <EmptyState
                        v-else
                        message="No cultural material information available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Stratigraphy"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasStratigraphy }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasStratigraphy"
                        :table-data="stratRows"
                        :column-definitions="stratColumns"
                    />
                    <EmptyState
                        v-else
                        message="No stratigraphy information available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Archaeological Culture"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasCulture }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasCulture"
                        :table-data="cultureRows"
                        :column-definitions="cultureColumns"
                        title="Archaeological Culture"
                    />
                    <EmptyState
                        v-else
                        message="No archaeological culture information available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Chronology"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasChronology }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasChronology"
                        :table-data="chronologyRows"
                        :column-definitions="chronologyColumns"
                    />
                    <EmptyState
                        v-else
                        message="No chronology information available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Discontinued Attributes (Radiocarbon)"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasHriaChronology }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasHriaChronology"
                        :table-data="hriaChronologyRows"
                        :column-definitions="hriaChronologyColumns"
                    />
                    <EmptyState
                        v-else
                        message="No discontinued chronology data available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Site Disturbance"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasDisturbance }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasDisturbance"
                        :table-data="disturbRows"
                        :column-definitions="disturbColumns"
                    />
                    <EmptyState
                        v-else
                        message="No site disturbance information available."
                    />
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>

<style scoped></style>
