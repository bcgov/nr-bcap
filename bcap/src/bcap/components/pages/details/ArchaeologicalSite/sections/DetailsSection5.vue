<script setup lang="ts">
import { computed, toRef } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import EmptyState from '@/bcap/components/EmptyState.vue';
import StandardDataTable from '@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue';
import type { AliasedTileDataWithAudit } from '@/bcgov_arches_common/types.ts';
import type { AliasedNodeData } from '@/arches_component_lab/types.ts';
import { isEmpty } from '@/bcap/util.ts';
import { useTileEditLog } from '@/bcgov_arches_common/composables/useTileEditLog.ts';
import type { EditLogData } from '@/bcgov_arches_common/types.ts';
import { EDIT_LOG_FIELDS } from '@/bcgov_arches_common/constants.ts';
import 'primeicons/primeicons.css';
import type { SiteBoundaryTile } from '@/bcap/schema/ArchaeologySiteSchema.ts';
import type { HriaDiscontinuedDataSchema } from '@/bcap/schema/HriaDiscontinuedDataSchema.ts';

const props = withDefaults(
    defineProps<{
        data: SiteBoundaryTile | undefined;
        hriaData: HriaDiscontinuedDataSchema | undefined;
        loading?: boolean;
        languageCode?: string;
        forceCollapsed?: boolean;
        editLogData?: EditLogData;
        showAuditFields?: boolean;
    }>(),
    {
        languageCode: 'en',
        loading: false,
        forceCollapsed: undefined,
        editLogData: () => ({}),
        showAuditFields: false,
    },
);

const currentSiteBoundaryData = computed(() => {
    return props.data ? [props.data] : [];
});

const { processedData: siteBoundaryWithAudit } = useTileEditLog(
    currentSiteBoundaryData,
    toRef(props, 'editLogData'),
);

const currentSiteBoundary = computed(() => {
    return siteBoundaryWithAudit.value?.[0]?.aliased_data;
});

const siteBoundaryDescriptionTableData = computed(() => {
    if (!siteBoundaryWithAudit.value?.[0]) return [];

    return [
        {
            ...siteBoundaryWithAudit.value[0],
            site_boundary_description:
                siteBoundaryWithAudit.value[0].aliased_data
                    ?.site_boundary_description,
        },
    ];
});

const hasDimensions = computed(() => {
    const dims = props.hriaData?.aliased_data?.site_dimensions?.aliased_data;
    if (!dims) return false;

    return (
        !isEmpty(dims.length) ||
        !isEmpty(dims.length_direction) ||
        !isEmpty(dims.width) ||
        !isEmpty(dims.width_direction) ||
        !isEmpty(dims.site_area) ||
        (!isEmpty(dims.boundary_type) && dims.boundary_type?.display_value)
    );
});

const hasBoundaryDescription = computed(() => {
    return (
        siteBoundaryDescriptionTableData.value?.some((item) => {
            const description = item.aliased_data?.site_boundary_description;

            if (!description || Array.isArray(description)) return false;

            const displayValue =
                'display_value' in description
                    ? description.display_value
                    : null;

            return (
                displayValue &&
                typeof displayValue === 'string' &&
                displayValue.trim() !== ''
            );
        }) ?? false
    );
});

const hasSpatialAccuracy = computed(() => {
    return (
        currentSiteBoundary.value &&
        (!isEmpty(
            currentSiteBoundary.value.latest_edit_type as AliasedNodeData,
        ) ||
            !isEmpty(
                currentSiteBoundary.value.accuracy_remarks as AliasedNodeData,
            ) ||
            !isEmpty(currentSiteBoundary.value.source_notes as AliasedNodeData))
    );
});

const hasSpatialAccuracyHistory = computed(() => {
    return siteBoundaryAnnotations.value.length > 0;
});

const siteBoundaryAnnotations = computed((): AliasedTileDataWithAudit[] => {
    const data = props.hriaData?.aliased_data as {
        site_boundary_annotations?: AliasedTileDataWithAudit[];
    };
    return data?.site_boundary_annotations ?? [];
});

const gisDimensionsTableData = computed(() => {
    const tile = props.hriaData?.aliased_data?.site_dimensions;
    if (!tile?.aliased_data) return [];

    return [
        {
            ...tile,
            length: tile.aliased_data.length,
            length_direction: tile.aliased_data.length_direction,
            width: tile.aliased_data.width,
            width_direction: tile.aliased_data.width_direction,
            site_area: tile.aliased_data.site_area,
        },
    ];
});

const discontinuedDimensionsTableData = computed(() => {
    return [];
});

const hasDiscontinuedDimensions = computed(() => {
    return discontinuedDimensionsTableData.value.length > 0;
});

const gisDimensionsColumns = [
    { field: 'length', label: 'Length (m)' },
    { field: 'length_direction', label: 'Length Direction' },
    { field: 'width', label: 'Width (m)' },
    { field: 'width_direction', label: 'Width Direction' },
    { field: 'site_area', label: 'Area (m²)' },
];

const discontinuedDimensionsColumns = [
    { field: 'length', label: 'Length' },
    { field: 'length_direction', label: 'Length Direction' },
    { field: 'width', label: 'Width' },
    { field: 'width_direction', label: 'Width Direction' },
    { field: 'boundary_type', label: 'Boundary Type' },
    { field: 'modified_on', label: 'Modified On' },
    { field: 'modified_by', label: 'Modified By' },
];

const siteBoundaryDescriptionColumns = computed(() => [
    {
        field: 'site_boundary_description',
        label: 'Site Boundary Description',
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
]);

const currentSpatialAccuracyColumns = computed(() => [
    { field: 'latest_edit_type', label: 'Edit Type' },
    { field: 'accuracy_remarks', label: 'Accuracy Remarks' },
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

const historicalSpatialAccuracyColumns = [
    { field: 'source_notes', label: 'Source Notes' },
    { field: 'accuracy_remarks', label: 'Accuracy Remarks' },
    { field: 'entered_on', label: 'Edited On', visible: props.showAuditFields },
    { field: 'entered_by', label: 'Edited By', visible: props.showAuditFields },
];
</script>

<template>
    <DetailsSection
        section-title="5. Site Boundary"
        :visible="true"
        :loading="props.loading"
        :force-collapsed="props.forceCollapsed"
    >
        <template #sectionContent>
            <DetailsSection
                section-title="GIS Calculated Dimensions"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasDimensions }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasDimensions"
                        :table-data="gisDimensionsTableData"
                        :column-definitions="gisDimensionsColumns"
                    />
                    <EmptyState
                        v-else
                        message="No dimension information available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Discontinued Attributes"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasDiscontinuedDimensions }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasDiscontinuedDimensions"
                        :table-data="discontinuedDimensionsTableData"
                        :column-definitions="discontinuedDimensionsColumns"
                        :initial-sort-field-index="5"
                    />
                    <EmptyState
                        v-else
                        message="No discontinued dimension information available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Site Boundary Description"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasBoundaryDescription }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasBoundaryDescription"
                        :table-data="siteBoundaryDescriptionTableData"
                        :column-definitions="siteBoundaryDescriptionColumns"
                    />
                    <EmptyState
                        v-else
                        message="No site boundary description available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Spatial Accuracy"
                variant="subsection"
                :visible="true"
                :class="{
                    'empty-section':
                        !hasSpatialAccuracy && !hasSpatialAccuracyHistory,
                }"
            >
                <template #sectionContent>
                    <div v-if="hasSpatialAccuracy || hasSpatialAccuracyHistory">
                        <DetailsSection
                            section-title="Current Spatial Accuracy"
                            variant="subsection"
                            :visible="true"
                            :class="{ 'empty-section': !hasSpatialAccuracy }"
                        >
                            <template #sectionContent>
                                <StandardDataTable
                                    v-if="hasSpatialAccuracy"
                                    :table-data="siteBoundaryWithAudit"
                                    :column-definitions="
                                        currentSpatialAccuracyColumns
                                    "
                                    :initial-sort-field-index="0"
                                />
                                <EmptyState
                                    v-else
                                    message="No current spatial accuracy information available."
                                />
                            </template>
                        </DetailsSection>

                        <DetailsSection
                            section-title="Historical Spatial Accuracy"
                            variant="subsection"
                            :visible="true"
                            :class="{
                                'empty-section': !hasSpatialAccuracyHistory,
                            }"
                        >
                            <template #sectionContent>
                                <StandardDataTable
                                    v-if="hasSpatialAccuracyHistory"
                                    :table-data="siteBoundaryAnnotations"
                                    :column-definitions="
                                        historicalSpatialAccuracyColumns
                                    "
                                    :initial-sort-field-index="2"
                                />
                                <EmptyState
                                    v-else
                                    message="No historical spatial accuracy records available."
                                />
                            </template>
                        </DetailsSection>
                    </div>
                    <EmptyState
                        v-else
                        message="No spatial accuracy information available."
                    />
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>
