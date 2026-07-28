<script setup lang="ts">
import WorkflowStepper from '@/bcap/apps/Permit/Modules/WorkflowStepper.vue';
import { GraphSlug } from '@/bcap/apps/Permit/graphSlug.ts';
import { useDraftStore } from '@/bcap/stores/draft.ts';
import { submitApplication } from '@/bcap/apps/Permit/api.ts';
import type { DraftNode } from '@/bcap/types.ts';
import type { PermitApplication } from '@/bcap/client/types.gen.ts';

import Step1_About from '@/bcap/apps/Permit/Modules/BaseModule/steps/Step1_About.vue';
import Step2_Prelim from '@/bcap/apps/Permit/Modules/BaseModule/steps/Step2_Prelim.vue';
import Step3_Contacts from '@/bcap/apps/Permit/Modules/BaseModule/steps/Step3_Contacts.vue';
import Step4_Details from '@/bcap/apps/Permit/Modules/BaseModule/steps/Step4_Details.vue';
import Step99_Review from '@/bcap/apps/Permit/Modules/BaseModule/steps/Step99_Review.vue';

const steps = [
    { label: 'Submission Information', component: Step1_About, heading: '' },
    { label: 'Preamble', component: Step2_Prelim },
    { label: 'Contacts', component: Step3_Contacts },
    { label: 'Details', component: Step4_Details, heading: 'Project Details' },
];

const draft = useDraftStore();

// The permit application is the root resource (no parent permit), so it creates
// a new permit rather than filing a module against one.
const submit = (): Promise<PermitApplication> => {
    if (!draft.draftId) throw new Error('No active draft found.');

    // Stamp the submission date: the server treats application_submission_date
    // as the "submitted" signal. Temporary until the backend owns this.
    draft.draftData.application_admin = {
        ...draft.draftData.application_admin,
        aliased_data: {
            ...draft.draftData.application_admin?.aliased_data,
            application_submission_date: {
                node_value: new Date().toISOString().slice(0, 10),
            } as DraftNode,
        },
    };

    return submitApplication(
        draft.draftId,
        draft.draftData,
        GraphSlug.PermitApplication,
    );
};
</script>

<template>
    <WorkflowStepper
        :graph-slug="GraphSlug.PermitApplication"
        title="Submit Filing"
        :steps="steps"
        :submit="submit"
        :review-component="Step99_Review"
    />
</template>
