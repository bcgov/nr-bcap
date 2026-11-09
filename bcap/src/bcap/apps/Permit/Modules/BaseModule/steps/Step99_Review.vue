<script setup lang="ts">
import Step99_Review from '@/bcap/apps/Permit/Modules/Step99_Review.vue';
import GenericReviewSummary from '@/bcap/apps/Permit/Modules/ReviewSummary.vue';
import type { ReviewField } from '@/bcap/apps/Permit/Modules/ReviewSummary.vue';
import type { ArchesDraftData } from '@/bcap/types.ts';
import type {
    BcapServiceRequestResourceAliasedData,
    GeojsonFeatureCollectionAliasedNodeData,
} from '@/bcap/client/types.gen.ts';

defineProps<{
    isSubmittedView?: boolean;
    resourceData?: ArchesDraftData | null;
}>();

const fields = (data: ArchesDraftData): ReviewField[] => {
    if (!data) return [];
    const sr = data as unknown as BcapServiceRequestResourceAliasedData;
    const ident = sr.service_request_identification?.aliased_data;
    const contacts = sr.service_request_contacts?.aliased_data;
    const project = sr.proposed_project?.aliased_data;
    const location = sr.project_location?.aliased_data;
    return [
        {
            label: 'Service Request Type',
            value: ident?.service_request_type?.display_value,
        },
        { label: 'Project Name', value: project?.project_name?.display_value },
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
        {
            label: 'Service Request Boundary',
            value: location?.service_request_boundary as
                GeojsonFeatureCollectionAliasedNodeData | null | undefined,
            type: 'map',
            graphSlug: 'bcap_service_request',
            nodeAlias: 'service_request_boundary',
        },
    ];
};

const isValid = () => true;
defineExpose({ isValid });
</script>

<template>
    <Step99_Review
        :is-submitted-view="isSubmittedView"
        :resource-data="resourceData"
    >
        <template #default="{ data }">
            <GenericReviewSummary :fields="fields(data)" />
        </template>
    </Step99_Review>
</template>
