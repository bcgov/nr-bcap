<script setup lang="ts">
import WorkflowStepper from '@/bcap/apps/Permit/Modules/WorkflowStepper.vue';
import { GraphSlug } from '@/bcap/apps/Permit/graphSlug.ts';
import Step1_About from '@/bcap/apps/Permit/Modules/DocumentSubmissionModule/steps/Step1_About.vue';
import Step2_Details from '@/bcap/apps/Permit/Modules/DocumentSubmissionModule/steps/Step2_Details.vue';
import Step3_Submission from '@/bcap/apps/Permit/Modules/DocumentSubmissionModule/steps/Step3_Submission.vue';
import Step4_Photographs from '@/bcap/apps/Permit/Modules/DocumentSubmissionModule/steps/Step4_Photographs.vue';
import CustomReview from '@/bcap/apps/Permit/Modules/DocumentSubmissionModule/steps/Step99_Review.vue';

import { useDraftStore } from '@/bcap/stores/draft.ts';
import { submitModule } from '@/bcap/apps/Permit/api.ts';

const draft = useDraftStore();

const steps = [
    { label: 'Setup / Disclaimer', component: Step1_About },
    { label: 'Submission Details', component: Step2_Details },
    { label: 'Document', component: Step3_Submission },
    { label: 'Photographs', component: Step4_Photographs },
];

const customDocumentSubmit = async () => {
    if (!draft.draftId) throw new Error('No active draft found.');
    if (!draft.parentPermitId)
        throw new Error('No permit associated with this filing.');

    const formattedPayload = JSON.parse(JSON.stringify(draft.draftData));
    const processAliasedData: Record<string, unknown> = {};

    if (formattedPayload.document_submission_process) {
        const existingNode = Array.isArray(
            formattedPayload.document_submission_process,
        )
            ? formattedPayload.document_submission_process[0]
            : formattedPayload.document_submission_process;

        if (
            existingNode?.aliased_data &&
            !Array.isArray(existingNode.aliased_data)
        ) {
            Object.assign(processAliasedData, existingNode.aliased_data);
        }
    }
    const nestedTiles = [
        'report_submission',
        'submission_photographs',
        'submission_assessment',
    ];

    nestedTiles.forEach((tileName) => {
        if (formattedPayload[tileName]) {
            // Force the data to be a object instead of array
            const tileData = Array.isArray(formattedPayload[tileName])
                ? formattedPayload[tileName][0]
                : formattedPayload[tileName];

            if (tileData) {
                processAliasedData[tileName] = tileData;
            }
            delete formattedPayload[tileName];
        }
    });

    formattedPayload.document_submission_process = [
        {
            aliased_data: processAliasedData,
        },
    ];

    return submitModule(
        draft.parentPermitId,
        draft.draftId,
        GraphSlug.DocumentSubmission,
        formattedPayload,
    );
};
</script>

<template>
    <WorkflowStepper
        :graph-slug="GraphSlug.DocumentSubmission"
        title="Document Submission"
        :steps="steps"
        :submit="customDocumentSubmit"
        :review-component="CustomReview"
    />
</template>
