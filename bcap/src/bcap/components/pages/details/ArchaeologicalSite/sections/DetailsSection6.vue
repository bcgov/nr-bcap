<script setup lang="ts">
import { computed, toRef } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import EmptyState from '@/bcap/components/EmptyState.vue';
import StandardDataTable from '@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue';
import { EDIT_LOG_FIELDS } from '@/bcgov_arches_common/constants.ts';
import { useHierarchicalData } from '@/bcap/composables/useHierarchicalData.ts';
import { useTileEditLog } from '@/bcgov_arches_common/composables/useTileEditLog.ts';
import type { ArchaeologicalDataTile } from '@/bcap/schema/ArchaeologySiteSchema.ts';
import type { EditLogData } from '@/bcgov_arches_common/types.ts';
import type { SiteVisitSchema } from '@/bcap/schema/SiteVisitSchema.ts';
import type { HriaDiscontinuedDataSchema } from '@/bcap/schema/HriaDiscontinuedDataSchema.ts';
import type { AliasedTileData } from '@/arches_component_lab/types.ts';
import 'primeicons/primeicons.css';

const props = withDefaults(
    defineProps<{
        data: ArchaeologicalDataTile | undefined;
        siteVisitData?: SiteVisitSchema[];
        hriaData?: HriaDiscontinuedDataSchema;
        loading?: boolean;
        languageCode?: string;
        forceCollapsed?: boolean;
        editLogData?: EditLogData;
        showAuditFields?: boolean;
    }>(),
    {
        siteVisitData: () => [],
        hriaData: undefined,
        languageCode: 'en',
        forceCollapsed: undefined,
        editLogData: () => ({}),
        showAuditFields: false,
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

const typologyRemarksColumns = computed(() => [
    { field: 'site_typology_remarks', label: 'Site Typology Remarks' },
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
]);

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

const stratColumns = [
    { field: 'stratigraphy', label: 'Stratigraphy Remarks', isHtml: true },
];

const cultureColumns = [
    { field: 'archaeological_culture', label: 'Archaeological Culture Name' },
    { field: 'culture_remarks', label: 'Remarks', isHtml: true },
];

const chronologyColumns = [
    { field: 'determination_method', label: 'Method' },
    { field: 'information_source', label: 'Source' },
    { field: 'chronology_remarks', label: 'Chronology Remarks', isHtml: true },
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
    { field: 'chronology_remarks', label: 'Chronology Remarks', isHtml: true },
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
    {
        field: 'disturbance_remarks',
        label: 'Disturbance Remarks',
        isHtml: true,
    },
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

const featuresData = computed(() => {
    const features: AliasedTileData[] = [];
    props.siteVisitData.forEach((visit) => {
        const arch = visit.aliased_data?.archaeological_data?.aliased_data;
        const featureRows = arch?.archaeological_feature || [];
        featureRows.forEach((feature) => {
            features.push(feature);
        });
    });
    return features;
});

const materialsData = computed(() => {
    const materials: AliasedTileData[] = [];
    props.siteVisitData.forEach((visit) => {
        const arch = visit.aliased_data?.archaeological_data?.aliased_data;
        const materialRows = arch?.cultural_material || [];
        materialRows.forEach((material) => {
            materials.push(material);
        });
    });
    return materials;
});

const stratigraphyData = computed(() => {
    const strat: AliasedTileData[] = [];
    props.siteVisitData.forEach((visit) => {
        const arch = visit.aliased_data?.archaeological_data?.aliased_data;
        const stratRows = arch?.stratigraphy || [];
        stratRows.forEach((s) => {
            strat.push(s);
        });
    });
    return strat;
});

const culturesData = computed(() => {
    const cultures: AliasedTileData[] = [];
    props.siteVisitData.forEach((visit) => {
        const arch = visit.aliased_data?.archaeological_data?.aliased_data;
        const cultureRows = arch?.archaeological_culture || [];
        cultureRows.forEach((culture) => {
            cultures.push(culture);
        });
    });
    return cultures;
});

const chronologiesData = computed(() => {
    const chronologies: AliasedTileData[] = [];
    props.siteVisitData.forEach((visit) => {
        const arch = visit.aliased_data?.archaeological_data?.aliased_data;
        const chronologyRows = arch?.chronology || [];
        chronologyRows.forEach((chronology) => {
            chronologies.push(chronology);
        });
    });
    return chronologies;
});

const hriaChronologiesData = computed(() => {
    return props.hriaData?.aliased_data?.chronology || [];
});

const disturbancesData = computed(() => {
    const disturbances: AliasedTileData[] = [];
    props.siteVisitData.forEach((visit) => {
        const arch = visit.aliased_data?.archaeological_data?.aliased_data;
        const disturbRows = arch?.site_disturbance || [];
        disturbRows.forEach((disturb) => {
            disturbances.push(disturb);
        });
    });
    return disturbances;
});

const hasTypology = computed(() => {
    return typologyTableData.value && typologyTableData.value.length > 0;
});

const hasTypologyRemarks = computed(() => {
    return (
        typologyRemarksTableData.value &&
        typologyRemarksTableData.value.length > 0
    );
});

const hasFeatures = computed(() => featuresData.value.length > 0);
const hasMaterials = computed(() => materialsData.value.length > 0);
const hasStratigraphy = computed(() => stratigraphyData.value.length > 0);
const hasCultures = computed(() => culturesData.value.length > 0);
const hasChronologies = computed(() => chronologiesData.value.length > 0);
const hasHriaChronologies = computed(
    () => hriaChronologiesData.value.length > 0,
);
const hasDisturbances = computed(() => disturbancesData.value.length > 0);
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

            <DetailsSection
                section-title="Archaeological Features"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasFeatures }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasFeatures"
                        :table-data="featuresData"
                        :column-definitions="featureColumns"
                        :initial-sort-field-index="0"
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
                :class="{ 'empty-section': !hasMaterials }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasMaterials"
                        :table-data="materialsData"
                        :column-definitions="materialColumns"
                        :initial-sort-field-index="0"
                    />
                    <EmptyState
                        v-else
                        message="No cultural material available."
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
                        :table-data="stratigraphyData"
                        :column-definitions="stratColumns"
                        :initial-sort-field-index="0"
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
                :class="{ 'empty-section': !hasCultures }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasCultures"
                        :table-data="culturesData"
                        :column-definitions="cultureColumns"
                        :initial-sort-field-index="0"
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
                :class="{ 'empty-section': !hasChronologies }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasChronologies"
                        :table-data="chronologiesData"
                        :column-definitions="chronologyColumns"
                        :initial-sort-field-index="0"
                    />
                    <EmptyState
                        v-else
                        message="No chronology information available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Chronology (Discontinued Attributes - Radiocarbon)"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasHriaChronologies }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasHriaChronologies"
                        :table-data="hriaChronologiesData"
                        :column-definitions="hriaChronologyColumns"
                        :initial-sort-field-index="0"
                    />
                    <EmptyState
                        v-else
                        message="No HRIA chronology information available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Disturbance"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasDisturbances }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasDisturbances"
                        :table-data="disturbancesData"
                        :column-definitions="disturbColumns"
                        :initial-sort-field-index="0"
                    />
                    <EmptyState
                        v-else
                        message="No disturbance information available."
                    />
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>
