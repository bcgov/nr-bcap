import { describe, it, expect, vi, beforeEach } from 'vitest';
import { shallowMount, flushPromises } from '@vue/test-utils';
import BaseModule from './BaseModule.vue';

// Own the submit mock so the date-stamp assertion can read it without a
// top-level import (which Vite resolves before the mock applies).
const { submitApplication } = vi.hoisted(() => ({
    submitApplication: vi.fn(),
}));

// 1. Mock the missing PrimeVue forms package so Vite doesn't crash during import analysis
vi.mock('@primevue/forms', () => ({
    FormField: { template: '<div />' },
}));

// 2. Mock the heavy Arches widgets (matching your other test setup)
vi.mock(
    '@/arches_component_lab/generics/GenericWidget/GenericWidget.vue',
    () => ({
        default: { name: 'GenericWidget', template: '<div />' },
    }),
);

vi.mock('@/arches_component_lab/widgets/constants.ts', () => ({
    EDIT: 'edit',
    VIEW: 'view',
}));

// 3. Mock vue-router so useRoute() doesn't crash
vi.mock('vue-router', () => ({
    useRoute: vi.fn(() => ({
        query: {}, // Simulate an empty query (no draftId)
    })),
}));

// 4. Mock utility functions
vi.mock('@/bcap/util.ts', () => ({
    getCsrfToken: vi.fn(() => 'mock-csrf-token'),
}));

// 5. Mock your API functions
vi.mock('@/bcap/apps/Permit/api.ts', () => ({
    submitApplication,
}));

describe('BaseModule.vue', () => {
    beforeEach(() => {
        vi.restoreAllMocks();

        // Mock global fetch to intercept the onMounted API calls
        vi.stubGlobal(
            'fetch',
            vi.fn(() =>
                Promise.resolve({
                    ok: true,
                    json: () =>
                        Promise.resolve({ id: 'mock-draft-id', data: {} }),
                } as Response),
            ),
        );
    });

    it('mounts the stepper workflow successfully', () => {
        // shallowMount automatically stubs all child components
        const wrapper = shallowMount(BaseModule);

        expect(wrapper.exists()).toBe(true);
        // Verify data hasn't loaded yet (which would show the spinner)
        expect(wrapper.vm.isDataLoaded).toBe(false);
    });

    it('creates a brand new draft on mount when no draftId is present', async () => {
        shallowMount(BaseModule);

        // Wait for the asynchronous onMounted hook to finish resolving its fetch calls
        await flushPromises();

        // Verify it tried to hit the POST endpoint to create a new draft
        expect(fetch).toHaveBeenCalledWith(
            '/bcap/api/resource_draft/permit_application',
            expect.objectContaining({
                method: 'POST',
            }),
        );
    });

    it('stamps today as the submission date before submitting', async () => {
        const wrapper = shallowMount(BaseModule);
        await flushPromises(); // mount creates the draft, setting draftId

        const submitted = await (
            wrapper.vm as unknown as {
                submitNewSiteData: () => Promise<boolean>;
            }
        ).submitNewSiteData();

        const today = new Date().toISOString().slice(0, 10);
        expect(submitted).toBe(true);
        // The server treats application_submission_date as the "submitted"
        // signal, so the draft must carry today's date (YYYY-MM-DD) on submit.
        expect(submitApplication).toHaveBeenCalledWith(
            'mock-draft-id',
            expect.objectContaining({
                application_admin: expect.objectContaining({
                    aliased_data: expect.objectContaining({
                        application_submission_date: { node_value: today },
                    }),
                }),
            }),
            expect.anything(),
        );
    });
});
