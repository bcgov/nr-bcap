<script setup lang="ts">
import { inject, computed, type Ref } from 'vue';
import FieldSet from 'primevue/fieldset';
import GenericReviewSummary, {
    type ReviewField,
} from '@/bcap/apps/Permit/Modules/ReviewSummary.vue';
import type { ArchesDraftData } from '@/bcap/types.ts';

const props = defineProps<{
    isSubmittedView?: boolean;
    resourceData?: ArchesDraftData | null;
}>();

const draftData = inject<Ref<ArchesDraftData>>('draftData');

const activeData = computed<ArchesDraftData>(() => {
    if (props.isSubmittedView && props.resourceData) return props.resourceData;
    return draftData?.value || ({} as ArchesDraftData);
});

const basicInfoFields = computed<ReviewField[]>(() => {
    // shortcuts for data nodes
    const ident = activeData.value?.application_identification?.aliased_data;
    const contacts = activeData.value?.application_contacts?.aliased_data;
    const project = activeData.value?.proposed_project?.aliased_data;
    const devDetails = project?.development_project_details?.aliased_data;
    const archPlan =
        activeData.value?.archaeological_assessment_plan?.aliased_data
            ?.section_1_overview?.aliased_data;
    const fnConsult = activeData.value?.first_nation_consultation?.aliased_data;

    return [
        // Identification
        {
            label: 'Replacement Application',
            value: ident?.is_replacement?.display_value,
        },
        { label: 'Project Name', value: ident?.project_name?.display_value },
        {
            label: 'Application ID',
            value: ident?.application_id?.display_value,
        },

        // Contacts
        {
            label: 'Application Proponent',
            value: contacts?.application_proponent?.display_value,
        },
        {
            label: 'Has Retained Archaeologist',
            value: contacts?.has_retained_archaeologist?.display_value,
        },
        {
            label: 'Rationale For No Archaeologist',
            value: contacts?.rationale_for_no_archaeologist?.display_value,
        },
        {
            label: 'Application Archaeologist',
            value: contacts?.application_archaeologist?.display_value,
        },

        // Proposed Project Details
        { label: 'Project Type', value: project?.project_type?.display_value },
        {
            label: 'Project Description',
            value: project?.project_description?.display_value,
            type: 'html',
        },
        {
            label: 'Scope of Work',
            value: project?.scope_of_work?.display_value,
            type: 'html',
        },

        // Archaeological Assessment & Consultation
        {
            label: 'Assessment Approach',
            value: archPlan?.assessment_approach?.display_value,
        },
        {
            label: 'First Nations File Numbers',
            value: fnConsult?.fn_file_numbers?.display_value,
        },

        // Development Specifics
        {
            label: 'Industrial Sector',
            value: devDetails?.industrial_sector?.display_value,
        },
        {
            label: 'Alteration Details',
            value: devDetails?.alteration_details?.display_value,
            type: 'html',
        },

        // Map Boundaries
        {
            label: 'Project Boundary',
            value: project?.project_boundary,
            type: 'map',
            nodeAlias: 'project_boundary',
        },
    ];
});

const isValid = () => true;
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

    <FieldSet class="review-fieldset">
        <GenericReviewSummary :fields="basicInfoFields" />
    </FieldSet>
</template>
