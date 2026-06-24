<script setup lang="ts">
import { inject, computed, type Ref } from 'vue';
import FieldSet from 'primevue/fieldset';
import GenericWidget from '@/arches_component_lab/generics/GenericWidget/GenericWidget.vue';
import { VIEW } from '@/arches_component_lab/widgets/constants.ts';
import type { CardXNodeXWidgetData } from '@/arches_component_lab/types.ts';
import type { ArchesDraftData } from '@/bcap/types.ts';

const props = defineProps<{
    isSubmittedView?: boolean;
    resourceData?: ArchesDraftData | null;
}>();

const draftData = inject<Ref<ArchesDraftData>>('draftData');

const activeData = computed<ArchesDraftData>(() => {
    if (props.isSubmittedView && props.resourceData) {
        return props.resourceData;
    }
    return draftData?.value || ({} as ArchesDraftData);
});

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
    <p
        v-if="!isSubmittedView"
        class="mb-4"
    >
        Please review the entered information prior to submitting the
        application:
    </p>
    <div
        v-else
        class="mb-4"
    >
        <p>
            Your application has been successfully submitted. Below is a summary
            of the finalized information.
        </p>
    </div>

    <FieldSet class="review-fieldset">
        <div class="div-grid-cols">
            <dt>Replacement Application</dt>
            <dd>
                {{
                    activeData?.application_identification?.aliased_data
                        ?.is_replacement?.display_value || ''
                }}
            </dd>

            <dt>Project Name</dt>
            <dd>
                {{
                    activeData?.application_identification?.aliased_data
                        ?.project_name?.display_value || ''
                }}
            </dd>

            <div v-if="isSubmittedView">
                <dt>Application ID</dt>
                <dd>
                    {{
                        activeData?.application_identification?.aliased_data
                            ?.application_id?.display_value || ''
                    }}
                </dd>
            </div>

            <dt>Application Proponent</dt>
            <dd>
                {{
                    activeData?.application_contacts?.aliased_data
                        ?.application_proponent?.display_value || ''
                }}
            </dd>

            <dt>Has Retained Archaeologist</dt>
            <dd>
                {{
                    activeData?.application_contacts?.aliased_data
                        ?.has_retained_archaeologist?.display_value || ''
                }}
            </dd>

            <template
                v-if="
                    activeData?.application_contacts?.aliased_data
                        ?.rationale_for_no_archaeologist?.display_value
                "
            >
                <dt>Rationale For No Archaeologist</dt>
                <dd>
                    {{
                        activeData?.application_contacts?.aliased_data
                            ?.rationale_for_no_archaeologist?.display_value ||
                        ''
                    }}
                </dd>
            </template>

            <template
                v-if="
                    activeData?.application_contacts?.aliased_data
                        ?.application_archaeologist?.display_value
                "
            >
                <dt>Application Archaeologist</dt>
                <dd>
                    {{
                        activeData?.application_contacts?.aliased_data
                            ?.application_archaeologist?.display_value || ''
                    }}
                </dd>
            </template>

            <dt>Project Type</dt>
            <dd>
                {{
                    activeData?.proposed_project?.aliased_data?.project_type
                        ?.display_value || ''
                }}
            </dd>

            <dt>Project Description</dt>
            <dd>
                {{
                    activeData?.proposed_project?.aliased_data
                        ?.project_description?.display_value || ''
                }}
            </dd>

            <dt>Scope of Work</dt>
            <dd>
                {{
                    activeData?.proposed_project?.aliased_data?.scope_of_work
                        ?.display_value || ''
                }}
            </dd>

            <dt>Assessment Approach</dt>
            <dd>
                {{
                    activeData?.archaeological_assessment_plan?.aliased_data
                        ?.section_1_overview?.aliased_data?.assessment_approach
                        ?.display_value || ''
                }}
            </dd>

            <dt>First Nations File Numbers</dt>
            <dd>
                {{
                    activeData?.first_nation_consultation?.aliased_data
                        ?.fn_file_numbers?.display_value || ''
                }}
            </dd>

            <dt>Industrial Sector</dt>
            <dd>
                {{
                    activeData?.proposed_project?.aliased_data
                        ?.development_project_details?.aliased_data
                        ?.industrial_sector?.display_value || ''
                }}
            </dd>

            <dt>Alteration Details</dt>
            <dd>
                {{
                    activeData?.proposed_project?.aliased_data
                        ?.development_project_details?.aliased_data
                        ?.alteration_details?.display_value || ''
                }}
            </dd>
        </div>

        <div class="map-section">
            <dt>Project Boundary</dt>
            <dd class="centered-map">
                <GenericWidget
                    v-if="
                        activeData?.proposed_project?.aliased_data
                            ?.project_boundary
                    "
                    :mode="VIEW"
                    :should-show-label="false"
                    :aliased-node-data="
                        activeData?.proposed_project?.aliased_data
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
