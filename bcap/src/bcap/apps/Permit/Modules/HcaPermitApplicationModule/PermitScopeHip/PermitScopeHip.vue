<script setup lang="ts">
import WorkflowStepper from '@/bcap/apps/Permit/Modules/WorkflowStepper.vue';
import { GraphSlug } from '@/bcap/apps/Permit/graphSlug.ts';
import { useDraftStore } from '@/bcap/stores/draft.ts';
import {
    createSectionDraft,
    fetchWorkflowSession,
    setRequirementStatus,
} from '@/bcap/apps/Permit/api.ts';
import { useRoute, useRouter } from 'vue-router';
import type { ArchesDraftData } from '@/bcap/types.ts';

import Step1_About from './steps/Step1_About.vue';
import Step2_ProposedDevelopment from './steps/Step2_ProposedDevelopment.vue';
import Step3_Objectives from './steps/Step3_Objectives.vue';
import Step4_ArchaeologicalStudies from './steps/Step4_ArchaeologicalStudies.vue';
import Step5_AlterationsDiscussion from './steps/Step5_AlterationsDiscussion.vue';

const SECTION = 'permit_scope';

const steps = [
    { label: 'About This Section', component: Step1_About },
    { label: 'Proposed Development', component: Step2_ProposedDevelopment },
    { label: 'Objectives', component: Step3_Objectives },
    { label: 'Archaeological Studies', component: Step4_ArchaeologicalStudies },
    {
        label: 'Alterations & Discussion',
        component: Step5_AlterationsDiscussion,
    },
];

const draft = useDraftStore();
const route = useRoute();
const router = useRouter();

const beforeRender = async () => {
    const isViewOnly = !!route.query.view;
    const requirementId = route.query.requirementId as string | undefined;
    const sessionId =
        (route.query.sessionId as string | undefined) ??
        (route.query.permit as string | undefined) ??
        requirementId ??
        crypto.randomUUID();
    try {
        let sectionDraft = null;
        try {
            const session = await fetchWorkflowSession(
                GraphSlug.HcaPermitApplication,
                sessionId,
            );
            sectionDraft =
                session.drafts.find((d) => d.section === SECTION) ?? null;
        } catch {
            // No session yet — fall through to create (or bail in view mode).
        }
        if (sectionDraft === null) {
            if (isViewOnly) return;
            sectionDraft = await createSectionDraft(
                GraphSlug.HcaPermitApplication,
                SECTION,
                sessionId,
            );
        }
        draft.loadDraft(
            sectionDraft.id,
            (sectionDraft.data || {}) as ArchesDraftData,
            sectionDraft.current_step || '',
        );
        if (!isViewOnly && !route.query.sessionId) {
            router.replace({ query: { ...route.query, sessionId } });
        }
    } catch {
        // The stepper's saveError banner will surface any subsequent save failure.
    }
};

const submit = async () => {
    await draft.saveNow();
    const requirementId = route.query.requirementId as string | undefined;
    if (requirementId) {
        await setRequirementStatus(requirementId, 'Completed');
    }
    return null;
};
</script>

<template>
    <WorkflowStepper
        :graph-slug="GraphSlug.HcaPermitApplication"
        title="HCA Permit Application — Permit Scope (HIP)"
        :steps="steps"
        submit-label="Save Section"
        :submit="submit"
        :view-only="!!route.query.view"
        :before-render="beforeRender"
    />
</template>
