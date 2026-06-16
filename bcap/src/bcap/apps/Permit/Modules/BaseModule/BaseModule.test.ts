import { describe, it, expect, vi, beforeEach } from 'vitest';
import { shallowMount, flushPromises } from '@vue/test-utils';
import BaseModule from './BaseModule.vue';

// 1. Mock vue-router so useRoute() doesn't crash
vi.mock('vue-router', () => ({
    useRoute: vi.fn(() => ({
        query: {}, // Simulate an empty query (no draftId)
    })),
}));

// 2. Mock utility functions
vi.mock('@/bcap/util.ts', () => ({
    getCsrfToken: vi.fn(() => 'mock-csrf-token'),
}));

// 3. Mock your API functions
vi.mock('@/bcap/apps/Permit/api.ts', () => ({
    submitApplication: vi.fn(),
}));

describe('BaseModule.vue', () => {
    beforeEach(() => {
        vi.restoreAllMocks();

        // 4. Mock global fetch to intercept the onMounted API calls
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
        // shallowMount automatically stubs all child components (Step1, Step2, Stepper, etc.)
        const wrapper = shallowMount(BaseModule);

        expect(wrapper.exists()).toBe(true);
        // Verify the loading spinner is present initially
        expect(wrapper.html()).toContain('progressspinner-stub');
    });

    it('creates a brand new draft on mount when no draftId is present', async () => {
        shallowMount(BaseModule);

        // Wait for the asynchronous onMounted hook to finish
        await flushPromises();

        // Verify it tried to hit the POST endpoint to create a new draft
        expect(fetch).toHaveBeenCalledWith(
            '/bcap/api/resource_draft/permit_application',
            expect.objectContaining({
                method: 'POST',
            }),
        );
    });
});
