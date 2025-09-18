<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";
import { getDisplayValue, isEmpty } from "@/bcap/util.ts";
import StandardDataTable from "@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue";
import "primeicons/primeicons.css";
import type { AliasedNodeData } from "@/arches_component_lab/types.ts";

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

const spatialAccuracyColumns = [
    { field: "latest_edit_type", label: "Edit Type" },
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
                section-title="5.1 GIS Calculated Dimensions"
                :visible="true"
            >
                <template #sectionContent>
                    <dl v-if="props.hriaData?.aliased_data?.site_dimensions?.aliased_data">
                        <dt v-if="!isEmpty(props.hriaData.aliased_data.site_dimensions.aliased_data.length)">Length (m)</dt>
                        <dd v-if="!isEmpty(props.hriaData.aliased_data.site_dimensions.aliased_data.length)">
                            {{ getDisplayValue(props.hriaData.aliased_data.site_dimensions.aliased_data.length) }}
                        </dd>

                        <dt v-if="!isEmpty(props.hriaData.aliased_data.site_dimensions.aliased_data.length_direction)">Length Direction</dt>
                        <dd v-if="!isEmpty(props.hriaData.aliased_data.site_dimensions.aliased_data.length_direction)">
                            {{ getDisplayValue(props.hriaData.aliased_data.site_dimensions.aliased_data.length_direction) }}
                        </dd>

                        <dt v-if="!isEmpty(props.hriaData.aliased_data.site_dimensions.aliased_data.width)">Width (m)</dt>
                        <dd v-if="!isEmpty(props.hriaData.aliased_data.site_dimensions.aliased_data.width)">
                            {{ getDisplayValue(props.hriaData.aliased_data.site_dimensions.aliased_data.width) }}
                        </dd>

                        <dt v-if="!isEmpty(props.hriaData.aliased_data.site_dimensions.aliased_data.width_direction)">Width Direction</dt>
                        <dd v-if="!isEmpty(props.hriaData.aliased_data.site_dimensions.aliased_data.width_direction)">
                            {{ getDisplayValue(props.hriaData.aliased_data.site_dimensions.aliased_data.width_direction) }}
                        </dd>

                        <dt v-if="!isEmpty(props.hriaData.aliased_data.site_dimensions.aliased_data.site_area)">Area (m²)</dt>
                        <dd v-if="!isEmpty(props.hriaData.aliased_data.site_dimensions.aliased_data.site_area)">
                            {{ getDisplayValue(props.hriaData.aliased_data.site_dimensions.aliased_data.site_area) }}
                        </dd>

                        <dt v-if="!isEmpty(props.hriaData.aliased_data.site_dimensions.aliased_data.boundary_type)">Boundary Type</dt>
                        <dd v-if="!isEmpty(props.hriaData.aliased_data.site_dimensions.aliased_data.boundary_type)">
                            {{ getDisplayValue(props.hriaData.aliased_data.site_dimensions.aliased_data.boundary_type) }}
                        </dd>
                    </dl>
                    <div v-else>
                        <p>No dimension information available.</p>
                    </div>
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="5.2 Site Boundary Description"
                :visible="true"
            >
                <template #sectionContent>
                    <dl v-if="props.data?.aliased_data">
                        <dt v-if="!isEmpty(props.data.aliased_data.source_notes)">Source Notes</dt>
                        <dd v-if="!isEmpty(props.data.aliased_data.source_notes)">
                            {{ getDisplayValue(props.data.aliased_data.source_notes) }}
                        </dd>
                    </dl>
                    <div v-else>
                        <p>No site boundary description available.</p>
                    </div>
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="5.3 Spatial Accuracy"
                :visible="true"
            >
                <template #sectionContent>
                    <dl v-if="props.data?.aliased_data">
                        <dt v-if="!isEmpty(props.data.aliased_data.latest_edit_type)">Latest Edit Type</dt>
                        <dd v-if="!isEmpty(props.data.aliased_data.latest_edit_type)">
                            {{ getDisplayValue(props.data.aliased_data.latest_edit_type) }}
                        </dd>

                        <dt v-if="!isEmpty(props.data.aliased_data.accuracy_remarks)">Accuracy Remarks</dt>
                        <dd v-if="!isEmpty(props.data.aliased_data.accuracy_remarks)">
                            {{ getDisplayValue(props.data.aliased_data.accuracy_remarks) }}
                        </dd>
                    </dl>
                    <div v-else>
                        <p>No spatial accuracy information available.</p>
                    </div>
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>
