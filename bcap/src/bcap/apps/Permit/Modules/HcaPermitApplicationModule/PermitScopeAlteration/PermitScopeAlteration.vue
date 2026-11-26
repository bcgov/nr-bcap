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
import Step2_ProjectDetails from './steps/Step2_ProjectDetails.vue';
import Step3_AffectedSites from './steps/Step3_AffectedSites.vue';
import Step4_RelatedAssessments from './steps/Step4_RelatedAssessments.vue';
import Step5_ImpactManagement from './steps/Step5_ImpactManagement.vue';
import Step6_PermitsDiscussion from './steps/Step6_PermitsDiscussion.vue';

const SECTION = 'permit_scope';

const steps = [
    { label: 'About This Section', component: Step1_About },
    { label: 'Project Details', component: Step2_ProjectDetails },
    { label: 'Affected Sites', component: Step3_AffectedSites },
    { label: 'Related Assessments', component: Step4_RelatedAssessments },
    { label: 'Impact Management', component: Step5_ImpactManagement },
    { label: 'Permits & Discussion', component: Step6_PermitsDiscussion },
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
        title="HCA Permit Application — Permit Scope (Alteration)"
        :steps="steps"
        submit-label="Save Section"
        :submit="submit"
        :view-only="!!route.query.view"
        :before-render="beforeRender"
    />
</template>
