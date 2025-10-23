<script setup lang="ts">
import { computed, toRef } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import EmptyState from '@/bcap/components/EmptyState.vue';
import StandardDataTable from '@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue';
import type { AliasedTileDataWithAudit } from '@/bcgov_arches_common/types.ts';
import type { AliasedNodeData } from '@/arches_component_lab/types.ts';
import { getDisplayValue, isEmpty } from '@/bcap/util.ts';
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
    }>(),
    {
        languageCode: 'en',
        loading: false,
        forceCollapsed: undefined,
        editLogData: () => ({}),
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

const hasDimensions = computed(() => {
    return props.hriaData?.aliased_data?.site_dimensions?.aliased_data;
});

const hasBoundaryDescription = computed(() => {
    return (
        currentSiteBoundary.value?.source_notes ||
        currentSiteBoundary.value?.site_boundary_description
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
    const history = currentSiteBoundary.value?.spatial_accuracy_history;
    return Array.isArray(history) && history.length > 0;
});

const siteBoundaryAnnotations = computed((): AliasedTileDataWithAudit[] => {
    const data = props.hriaData?.aliased_data as {
        site_boundary_annotations?: AliasedTileDataWithAudit[];
    };
    return data?.site_boundary_annotations ?? [];
});

const hasHistoricalSpatialAccuracy = computed(() => {
    return siteBoundaryAnnotations.value.length > 0;
});

const currentSpatialAccuracyColumns = [
    { field: 'source_notes', label: 'Source Notes' },
    { field: 'latest_edit_type', label: 'Edit Type' },
    { field: 'accuracy_remarks', label: 'Accuracy Remarks' },
    { field: EDIT_LOG_FIELDS.ENTERED_ON, label: 'Entered On' },
    { field: EDIT_LOG_FIELDS.ENTERED_BY, label: 'Entered By' },
];

const spatialAccuracyColumns = [
    { field: 'edit_type', label: 'Edit Type' },
    { field: 'accuracy_remarks', label: 'Accuracy Remarks' },
    { field: 'edited_on', label: 'Edited On' },
    { field: 'edited_by', label: 'Edited By' },
];

const historicalSpatialAccuracyColumns = [
    { field: 'source_notes', label: 'Source Notes' },
    { field: 'latest_edit_type', label: 'Edit Type' },
    { field: 'accuracy_remarks', label: 'Accuracy Remarks' },
    { field: 'entered_on', label: 'Entered On' },
    { field: 'entered_by', label: 'Entered By' },
];
</script>

<template>
    <DetailsSection
        section-title="5. Site Boundary Details"
        :loading="props.loading"
        :visible="true"
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
                    <dl v-if="hasDimensions">
                        <dt
                            v-if="
                                !isEmpty(
                                    props.hriaData?.aliased_data
                                        ?.site_dimensions?.aliased_data?.length,
                                )
                            "
                        >
                            Length (m)
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    props.hriaData?.aliased_data
                                        ?.site_dimensions?.aliased_data?.length,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    props.hriaData?.aliased_data
                                        ?.site_dimensions?.aliased_data?.length,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    props.hriaData?.aliased_data
                                        ?.site_dimensions?.aliased_data
                                        ?.length_direction,
                                )
                            "
                        >
                            Length Direction
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    props.hriaData?.aliased_data
                                        ?.site_dimensions?.aliased_data
                                        ?.length_direction,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    props.hriaData?.aliased_data
                                        ?.site_dimensions?.aliased_data
                                        ?.length_direction,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    props.hriaData?.aliased_data
                                        ?.site_dimensions?.aliased_data?.width,
                                )
                            "
                        >
                            Width (m)
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    props.hriaData?.aliased_data
                                        ?.site_dimensions?.aliased_data?.width,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    props.hriaData?.aliased_data
                                        ?.site_dimensions?.aliased_data?.width,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    props.hriaData?.aliased_data
                                        ?.site_dimensions?.aliased_data
                                        ?.width_direction,
                                )
                            "
                        >
                            Width Direction
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    props.hriaData?.aliased_data
                                        ?.site_dimensions?.aliased_data
                                        ?.width_direction,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    props.hriaData?.aliased_data
                                        ?.site_dimensions?.aliased_data
                                        ?.width_direction,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    props.hriaData?.aliased_data
                                        ?.site_dimensions?.aliased_data
                                        ?.site_area,
                                )
                            "
                        >
                            Area (m²)
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    props.hriaData?.aliased_data
                                        ?.site_dimensions?.aliased_data
                                        ?.site_area,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    props.hriaData?.aliased_data
                                        ?.site_dimensions?.aliased_data
                                        ?.site_area,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    props.hriaData?.aliased_data
                                        ?.site_dimensions?.aliased_data
                                        ?.boundary_type,
                                )
                            "
                        >
                            Boundary Type
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    props.hriaData?.aliased_data
                                        ?.site_dimensions?.aliased_data
                                        ?.boundary_type,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    props.hriaData?.aliased_data
                                        ?.site_dimensions?.aliased_data
                                        ?.boundary_type,
                                )
                            }}
                        </dd>
                    </dl>
                    <EmptyState
                        v-else
                        message="No dimension information available."
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
                    <dl v-if="hasBoundaryDescription">
                        <dt
                            v-if="
                                !isEmpty(
                                    currentSiteBoundary?.source_notes as AliasedNodeData,
                                )
                            "
                        >
                            Source Notes
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    currentSiteBoundary?.source_notes as AliasedNodeData,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    currentSiteBoundary?.source_notes as AliasedNodeData,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    currentSiteBoundary?.site_boundary_description as AliasedNodeData,
                                )
                            "
                        >
                            Site Boundary Description
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    currentSiteBoundary?.site_boundary_description as AliasedNodeData,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    currentSiteBoundary?.site_boundary_description as AliasedNodeData,
                                )
                            }}
                        </dd>
                    </dl>
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
                                'empty-section':
                                    !hasSpatialAccuracyHistory &&
                                    !hasHistoricalSpatialAccuracy,
                            }"
                        >
                            <template #sectionContent>
                                <div
                                    v-if="
                                        hasSpatialAccuracyHistory ||
                                        hasHistoricalSpatialAccuracy
                                    "
                                >
                                    <StandardDataTable
                                        v-if="hasSpatialAccuracyHistory"
                                        :table-data="
                                            (currentSiteBoundary?.spatial_accuracy_history as AliasedTileDataWithAudit[]) ??
                                            []
                                        "
                                        :column-definitions="
                                            spatialAccuracyColumns
                                        "
                                        :initial-sort-field-index="2"
                                    />

                                    <StandardDataTable
                                        v-if="hasHistoricalSpatialAccuracy"
                                        :table-data="siteBoundaryAnnotations"
                                        :column-definitions="
                                            historicalSpatialAccuracyColumns
                                        "
                                        :initial-sort-field-index="3"
                                    />
                                </div>
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
