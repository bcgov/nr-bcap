<script setup lang="ts">
import WorkflowStepper from '@/bcap/apps/Permit/Modules/WorkflowStepper.vue';
import { GraphSlug } from '@/bcap/apps/Permit/graphSlug.ts';
import { useDraftStore } from '@/bcap/stores/draft.ts';
import {
    submitServiceRequest,
    setRequirementStatus,
} from '@/bcap/apps/Permit/api.ts';
import type {
    BcapServiceRequest,
    BcapServiceRequestResourceAliasedDataWritable as BcapServiceRequestDraftData,
} from '@/bcap/client/types.gen.ts';
import { useRoute } from 'vue-router';

import Step1_About from '@/bcap/apps/Permit/Modules/BaseModule/steps/Step1_About.vue';
import Step2_Prelim from '@/bcap/apps/Permit/Modules/BaseModule/steps/Step2_Prelim.vue';
// import Step3_Contacts from '@/bcap/apps/Permit/Modules/BaseModule/steps/Step3_Contacts.vue';
import Step4_Location from '@/bcap/apps/Permit/Modules/BaseModule/steps/Step4_Location.vue';
import Step5_Details from '@/bcap/apps/Permit/Modules/BaseModule/steps/Step5_Details.vue';
import Step99_Review from '@/bcap/apps/Permit/Modules/BaseModule/steps/Step99_Review.vue';
import { UserFacingError } from '@/bcap/api.ts';

const steps = [
    { label: 'Submission Information', component: Step1_About, heading: '' },
    { label: 'Preamble', component: Step2_Prelim },
    // { label: 'Contacts', component: Step3_Contacts },
    { label: 'Property Information', component: Step4_Location },
    {
        label: 'Spatial Location',
        component: Step5_Details,
    },
];

const draft = useDraftStore();
const route = useRoute();

// Creates a new service request (no parent permit). Marks the opening
// process requirement satisfied after saving so "View Submission" appears.
const submit = async (): Promise<BcapServiceRequest> => {
    if (!draft.draftId) throw new UserFacingError('No active draft found.');

    // Stamp the submission date: the server treats application_submission_date
    // as the "submitted" signal. Temporary until the backend owns this.
    const srDraft = draft.draftData as BcapServiceRequestDraftData;
    srDraft.service_request_admin = {
        ...srDraft.service_request_admin,
        aliased_data: {
            ...srDraft.service_request_admin?.aliased_data,
            application_submission_date: {
                node_value: new Date().toISOString().slice(0, 10),
            },
        },
    };

    const result = await submitServiceRequest(
        draft.draftId,
        draft.draftData,
        GraphSlug.BcapServiceRequest,
    );

    const requirementId = route.query.requirementId as string | undefined;
    if (requirementId) {
        await setRequirementStatus(requirementId, 'Completed');
    }

    return result;
};
</script>

<template>
    <WorkflowStepper
        :graph-slug="GraphSlug.BcapServiceRequest"
        title="Submit Service Request"
        :steps="steps"
        :submit="submit"
        :review-component="Step99_Review"
    />
</template>
