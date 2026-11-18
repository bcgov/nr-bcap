<script setup lang="ts">
import { onMounted } from 'vue';
import WorkflowStepper from '@/bcap/apps/Permit/Modules/WorkflowStepper.vue';
import { GraphSlug } from '@/bcap/apps/Permit/graphSlug.ts';
import { useDraftStore } from '@/bcap/stores/draft.ts';
import { createSectionDraft } from '@/bcap/apps/Permit/api.ts';
import { useRoute, useRouter } from 'vue-router';
import type { ArchesDraftData } from '@/bcap/types.ts';

import Step1_Overview from './steps/Step1_Overview.vue';

const SECTION = 'application_overview';

const steps = [{ label: 'Application Overview', component: Step1_Overview }];

const draft = useDraftStore();
const route = useRoute();
const router = useRouter();

// WorkflowStepper handles ?draftId= loading in its own onMounted. This runs
// after that so a section draft is only created when no draft was resumed.
// The draft_session_id groups all section drafts for a single HCA application.
onMounted(async () => {
    if (route.query.draftId) return;
    const sessionId =
        (route.query.sessionId as string | undefined) ?? crypto.randomUUID();
    try {
        const sectionDraft = await createSectionDraft(
            GraphSlug.HcaPermitApplication,
            SECTION,
            sessionId,
        );
        draft.loadDraft(
            sectionDraft.id,
            (sectionDraft.data || {}) as ArchesDraftData,
            sectionDraft.current_step || '',
        );
        if (!route.query.sessionId) {
            router.replace({ query: { ...route.query, sessionId } });
        }
    } catch {
        // The stepper's saveError banner will surface any subsequent save failure.
    }
});

// Save the current section draft and return. The full HCA Permit Application
// submission (creating the resource from all section drafts) is handled
// separately once all sections are complete.
const submit = async () => {
    await draft.saveNow();
    return null;
};
</script>

<template>
    <WorkflowStepper
        :graph-slug="GraphSlug.HcaPermitApplication"
        title="HCA Permit Application — Application Overview"
        :steps="steps"
        submit-label="Save Section"
        :submit="submit"
    />
</template>
