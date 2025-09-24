<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";
import EmptyState from "@/bcap/components/EmptyState.vue";
import StandardDataTable from "@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue";
import { getDisplayValue, isEmpty } from "@/bcap/util.ts";
import "primeicons/primeicons.css";

const props = withDefaults(
    defineProps<{
        data: any;
        hriaData: any;
        loading?: boolean;
        languageCode?: string;
    }>(),
    {
        languageCode: "en",
    },
);

const hasDimensions = computed(() => {
    return props.hriaData?.aliased_data?.site_dimensions?.aliased_data;
});

const hasBoundaryDescription = computed(() => {
    return (
        props.data?.aliased_data?.source_notes ||
        props.data?.aliased_data?.site_boundary_description
    );
});

const hasSpatialAccuracy = computed(() => {
    return (
        props.data?.aliased_data &&
        (!isEmpty(props.data.aliased_data.latest_edit_type) ||
            !isEmpty(props.data.aliased_data.accuracy_remarks))
    );
});

const hasSpatialAccuracyHistory = computed(() => {
    return (
        props.data?.aliased_data?.spatial_accuracy_history &&
        props.data.aliased_data.spatial_accuracy_history.length > 0
    );
});

const spatialAccuracyColumns = [
    { field: "edit_type", label: "Edit Type" },
    { field: "accuracy_remarks", label: "Accuracy Remarks" },
    { field: "edited_on", label: "Edited On" },
    { field: "edited_by", label: "Edited By" },
];
</script>

<template>
    <DetailsSection
        section-title="5. Site Boundary Details"
        :loading="props.loading"
        :visible="true"
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
                                    props.hriaData.aliased_data.site_dimensions
                                        .aliased_data.length,
                                )
                            "
                        >
                            Length (m)
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    props.hriaData.aliased_data.site_dimensions
                                        .aliased_data.length,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    props.hriaData.aliased_data.site_dimensions
                                        .aliased_data.length,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    props.hriaData.aliased_data.site_dimensions
                                        .aliased_data.length_direction,
                                )
                            "
                        >
                            Length Direction
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    props.hriaData.aliased_data.site_dimensions
                                        .aliased_data.length_direction,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    props.hriaData.aliased_data.site_dimensions
                                        .aliased_data.length_direction,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    props.hriaData.aliased_data.site_dimensions
                                        .aliased_data.width,
                                )
                            "
                        >
                            Width (m)
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    props.hriaData.aliased_data.site_dimensions
                                        .aliased_data.width,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    props.hriaData.aliased_data.site_dimensions
                                        .aliased_data.width,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    props.hriaData.aliased_data.site_dimensions
                                        .aliased_data.width_direction,
                                )
                            "
                        >
                            Width Direction
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    props.hriaData.aliased_data.site_dimensions
                                        .aliased_data.width_direction,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    props.hriaData.aliased_data.site_dimensions
                                        .aliased_data.width_direction,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    props.hriaData.aliased_data.site_dimensions
                                        .aliased_data.site_area,
                                )
                            "
                        >
                            Area (m²)
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    props.hriaData.aliased_data.site_dimensions
                                        .aliased_data.site_area,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    props.hriaData.aliased_data.site_dimensions
                                        .aliased_data.site_area,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    props.hriaData.aliased_data.site_dimensions
                                        .aliased_data.boundary_type,
                                )
                            "
                        >
                            Boundary Type
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    props.hriaData.aliased_data.site_dimensions
                                        .aliased_data.boundary_type,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    props.hriaData.aliased_data.site_dimensions
                                        .aliased_data.boundary_type,
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
                                !isEmpty(props.data.aliased_data.source_notes)
                            "
                        >
                            Source Notes
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(props.data.aliased_data.source_notes)
                            "
                        >
                            {{
                                getDisplayValue(
                                    props.data.aliased_data.source_notes,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    props.data.aliased_data
                                        .site_boundary_description,
                                )
                            "
                        >
                            Site Boundary Description
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    props.data.aliased_data
                                        .site_boundary_description,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    props.data.aliased_data
                                        .site_boundary_description,
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
                                <dl v-if="hasSpatialAccuracy">
                                    <dt
                                        v-if="
                                            !isEmpty(
                                                props.data.aliased_data
                                                    .latest_edit_type,
                                            )
                                        "
                                    >
                                        Latest Edit Type
                                    </dt>
                                    <dd
                                        v-if="
                                            !isEmpty(
                                                props.data.aliased_data
                                                    .latest_edit_type,
                                            )
                                        "
                                    >
                                        {{
                                            getDisplayValue(
                                                props.data.aliased_data
                                                    .latest_edit_type,
                                            )
                                        }}
                                    </dd>

                                    <dt
                                        v-if="
                                            !isEmpty(
                                                props.data.aliased_data
                                                    .accuracy_remarks,
                                            )
                                        "
                                    >
                                        Accuracy Remarks
                                    </dt>
                                    <dd
                                        v-if="
                                            !isEmpty(
                                                props.data.aliased_data
                                                    .accuracy_remarks,
                                            )
                                        "
                                    >
                                        {{
                                            getDisplayValue(
                                                props.data.aliased_data
                                                    .accuracy_remarks,
                                            )
                                        }}
                                    </dd>
                                </dl>
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
                                    :table-data="
                                        props.data.aliased_data
                                            .spatial_accuracy_history ?? []
                                    "
                                    :column-definitions="spatialAccuracyColumns"
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
