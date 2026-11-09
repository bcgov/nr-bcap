import { shallowMount } from '@vue/test-utils';
import BaseModule from './BaseModule.vue';
import WorkflowStepper from '@/bcap/apps/Permit/Modules/WorkflowStepper.vue';
import { useDraftStore } from '@/bcap/stores/draft.ts';

// Own the submit mock so the date-stamp assertion can read it without a
// top-level import (which Vite resolves before the mock applies).
const { submitServiceRequest } = vi.hoisted(() => ({
    submitServiceRequest: vi.fn(),
}));

vi.mock('@primevue/forms', () => ({
    FormField: { template: '<div />' },
}));

vi.mock('vue-router', () => ({
    useRoute: vi.fn(() => ({
        query: {}, // Simulate an empty query (no draftId)
    })),
}));

vi.mock('@/bcap/util.ts', () => ({
    getCsrfToken: vi.fn(() => 'mock-csrf-token'),
}));

vi.mock('@/bcap/apps/Permit/api.ts', async (importOriginal) => ({
    ...(await importOriginal<typeof import('@/bcap/apps/Permit/api.ts')>()),
    submitServiceRequest,
}));

describe('BaseModule.vue', () => {
    beforeEach(() => {
        vi.restoreAllMocks();
    });

    it('drives the service request through the shared workflow stepper', () => {
        const wrapper = shallowMount(BaseModule);

        const stepper = wrapper.findComponent(WorkflowStepper);
        expect(stepper.exists()).toBe(true);
        expect(stepper.props('graphSlug')).toBe('bcap_service_request');
    });

    it('stamps today as the submission date before submitting', async () => {
        const wrapper = shallowMount(BaseModule);

        // Submit requires an existing draft; simulate one the first edit would
        // have created via the store.
        useDraftStore().loadDraft('mock-draft-id', {});

        // BaseModule owns only the submit strategy; the stepper shell invokes it
        // on the final step.
        const submit = wrapper
            .findComponent(WorkflowStepper)
            .props('submit') as () => Promise<unknown>;
        await submit();

        const today = new Date().toISOString().slice(0, 10);
        // The server treats application_submission_date as the "submitted"
        // signal, so the draft must carry today's date (YYYY-MM-DD) on submit.
        expect(submitServiceRequest).toHaveBeenCalledWith(
            'mock-draft-id',
            expect.objectContaining({
                service_request_admin: expect.objectContaining({
                    aliased_data: expect.objectContaining({
                        application_submission_date: { node_value: today },
                    }),
                }),
            }),
            expect.anything(),
        );
    });
});
