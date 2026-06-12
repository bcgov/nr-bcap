<script setup lang="ts">
import { inject, type Ref } from 'vue';
import FieldSet from 'primevue/fieldset';
import GenericWidget from '@/arches_component_lab/generics/GenericWidget/GenericWidget.vue';
import { VIEW } from '@/arches_component_lab/widgets/constants.ts';
import type { CardXNodeXWidgetData } from '@/arches_component_lab/types.ts';
import type { ArchesDraftData } from '@/bcap/types.ts';

const draftData = inject<Ref<ArchesDraftData>>('draftData');

const isValid = () => {
    return true;
};

const mapOverrides = {
    widget: {
        widgetid: '',
        component:
            'bcgov_arches_common/widgets/MapDropZoneWidget/MapDropZoneWidget.vue',
    },
} satisfies Partial<CardXNodeXWidgetData>;

defineExpose({ isValid });
</script>

<template>
    <p class="mb-4">
        Please review the entered information prior to submitting the
        application:
    </p>

    <FieldSet class="review-fieldset">
        <div class="div-grid-cols">
            <dt>Replacement Application</dt>
            <dd>
                {{
                    draftData?.application_identification?.aliased_data
                        ?.is_replacement?.display_value || ''
                }}
            </dd>

            <dt>Project Name</dt>
            <dd>
                {{
                    draftData?.application_identification?.aliased_data
                        ?.project_name?.display_value || ''
                }}
            </dd>

            <dt>Application ID</dt>
            <dd>
                {{
                    draftData?.application_identification?.aliased_data
                        ?.application_id?.display_value || ''
                }}
            </dd>

            <dt>Project Type</dt>
            <dd>
                {{
                    draftData?.proposed_project?.aliased_data?.project_type
                        ?.display_value || ''
                }}
            </dd>

            <dt>Project Description</dt>
            <dd
                v-html="
                    draftData?.proposed_project?.aliased_data
                        ?.project_description?.display_value || ''
                "
            ></dd>

            <dt>Scope of Work</dt>
            <dd
                v-html="
                    draftData?.proposed_project?.aliased_data?.scope_of_work
                        ?.display_value || ''
                "
            ></dd>

            <dt>Assessment Approach</dt>
            <dd>
                {{
                    draftData?.archaeological_assessment_plan?.aliased_data
                        ?.section_1_overview?.aliased_data?.assessment_approach
                        ?.display_value || ''
                }}
            </dd>

            <dt>First Nations File Numbers</dt>
            <dd>
                {{
                    draftData?.first_nation_consultation?.aliased_data
                        ?.fn_file_numbers?.display_value || ''
                }}
            </dd>

            <dt>Industrial Sector</dt>
            <dd>
                {{
                    draftData?.proposed_project?.aliased_data
                        ?.development_project_details?.aliased_data
                        ?.industrial_sector?.display_value || ''
                }}
            </dd>

            <dt>Alteration Details</dt>
            <dd
                v-html="
                    draftData?.proposed_project?.aliased_data
                        ?.development_project_details?.aliased_data
                        ?.alteration_details?.display_value || ''
                "
            ></dd>
        </div>

        <div class="map-section">
            <dt>Project Boundary</dt>
            <dd class="centered-map">
                <GenericWidget
                    v-if="
                        draftData?.proposed_project?.aliased_data
                            ?.project_boundary
                    "
                    :mode="VIEW"
                    :should-show-label="false"
                    :aliased-node-data="
                        draftData?.proposed_project?.aliased_data
                            ?.project_boundary
                    "
                    :card-x-node-x-widget-data-overrides="mapOverrides"
                    graph-slug="permit_application"
                    node-alias="project_boundary"
                />
                <span v-else>No boundary provided</span>
            </dd>
        </div>
    </FieldSet>
</template>

<style scoped>
.review-fieldset {
    margin-bottom: 2rem;
}

.div-grid-cols {
    display: grid;
    grid-template-columns: 200px 1fr;
    gap: 1rem;
    align-items: start;
}

.map-section {
    padding-top: 1.5rem;
    width: 100%;
    display: block;
}
</style>
