<script setup lang="ts">
import { onMounted } from 'vue';
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

import Step1_Contacts from './steps/Step1_Contacts.vue';
import Step2_Overview from './steps/Step2_Overview.vue';

const SECTION = 'application_contacts';

const steps = [
    { label: 'Application Contacts', component: Step1_Contacts },
    { label: 'Application Overview', component: Step2_Overview },
];

const draft = useDraftStore();
const route = useRoute();
const router = useRouter();

// WorkflowStepper handles ?draftId= loading in its own onMounted. This runs
// after that so a section draft is only created when no draft was resumed.
// The draft_session_id groups all section drafts for a single HCA application.
// requirementId is used as the stable session key so returning via Edit reloads
// the same section drafts that were saved on first completion.
onMounted(async () => {
    if (route.query.draftId) return;
    const isViewOnly = !!route.query.view;
    const requirementId = route.query.requirementId as string | undefined;
    const sessionId =
        (route.query.sessionId as string | undefined) ??
        requirementId ??
        crypto.randomUUID();
    try {
        // Check for an existing section draft before creating a new one — the
        // backend rejects a second create for the same (session_id, section)
        // with a 409. If one already exists, resume from it.
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
            if (isViewOnly) return; // Nothing to view yet.
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
});

// Save the current section draft and mark the linked requirement Completed.
// The full HCA Permit Application submission (creating the resource from all
// section drafts) is handled separately once all sections are complete.
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
        title="HCA Permit Application — Permit Info"
        :steps="steps"
        submit-label="Save Section"
        :submit="submit"
        :view-only="!!route.query.view"
    />
</template>
