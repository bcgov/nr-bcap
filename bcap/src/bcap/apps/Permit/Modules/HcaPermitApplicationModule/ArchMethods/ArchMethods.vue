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

import Step1_ResearchDesign from './steps/Step1_ResearchDesign.vue';
import Step2_SurveyCoverage from './steps/Step2_SurveyCoverage.vue';
import Step3_SubsurfaceTesting from './steps/Step3_SubsurfaceTesting.vue';
import Step4_MachineAssistedMethods from './steps/Step4_MachineAssistedMethods.vue';
import Step5_WinterMethods from './steps/Step5_WinterMethods.vue';
import Step6_OtherFieldMethods from './steps/Step6_OtherFieldMethods.vue';

const SECTION = 'methodology';

const steps = [
    {
        label: 'Research Design & Field Methods',
        component: Step1_ResearchDesign,
    },
    {
        label: 'Survey Coverage & Archaeological Potential',
        component: Step2_SurveyCoverage,
    },
    { label: 'Subsurface Testing', component: Step3_SubsurfaceTesting },
    {
        label: 'Machine-Assisted Methods',
        component: Step4_MachineAssistedMethods,
    },
    { label: 'Winter Methods', component: Step5_WinterMethods },
    { label: 'Other Field Methods', component: Step6_OtherFieldMethods },
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
        title="HCA Permit Application — Methods"
        :steps="steps"
        submit-label="Save Section"
        :submit="submit"
        :view-only="!!route.query.view"
        :before-render="beforeRender"
    />
</template>
