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
import { fileParts } from '@/bcap/util.ts';
import type {
    DocumentSubmissionDocumentSubmissionProcessAliasedDataWritable as ProcessAliasedData,
    DocumentSubmissionDocumentSubmissionProcessTileWritable as ProcessTile,
    DocumentSubmissionReportSubmissionTileWritable as ReportTile,
    DocumentSubmissionSubmissionAssessmentTileWritable as AssessmentTile,
    DocumentSubmissionSubmissionPhotographsTileWritable as PhotographTile,
} from '@/bcap/client/types.gen.ts';

const draft = useDraftStore();

const steps = [
    { label: 'Setup / Disclaimer', component: Step1_About },
    { label: 'Submission Details', component: Step2_Details },
    { label: 'Document', component: Step3_Submission },
    { label: 'Photographs', component: Step4_Photographs },
];

interface DocumentSubmissionDraft {
    document_submission_process?: ProcessTile | null;
    report_submission?: ReportTile | null;
    submission_photographs?: PhotographTile[] | null;
    submission_assessment?: AssessmentTile | null;
}

const customDocumentSubmit = async () => {
    if (!draft.draftId) throw new Error('No active draft found.');
    if (!draft.parentPermitId)
        throw new Error('No permit associated with this filing.');

    const draftData: DocumentSubmissionDraft = draft.draftData;
    const process = draftData.document_submission_process?.aliased_data;

    const report = draftData.report_submission ?? null;
    const photographs = draftData.submission_photographs ?? [];

    const aliasedData: ProcessAliasedData = {
        submission_type: process?.submission_type ?? null,
        submission_number: process?.submission_number ?? null,
        report_submission: report,
        submission_photographs: photographs,
        submission_assessment: draftData.submission_assessment ?? null,
    };

    const files = [
        ...(report ? fileParts(report, report.aliased_data?.report_file) : []),
        ...photographs.flatMap((photograph) =>
            fileParts(
                photograph,
                photograph.aliased_data?.submission_photographs,
            ),
        ),
    ];

    return submitModule(
        draft.parentPermitId,
        draft.draftId,
        GraphSlug.DocumentSubmission,
        { document_submission_process: [{ aliased_data: aliasedData }] },
        files,
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
