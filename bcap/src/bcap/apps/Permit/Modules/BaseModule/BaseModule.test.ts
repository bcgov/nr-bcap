import { describe, it, expect, vi, beforeEach } from 'vitest';
import { shallowMount, flushPromises } from '@vue/test-utils';
import BaseModule from './BaseModule.vue';

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
    submitApplication: vi.fn(),
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
        // Verify the loading spinner is present initially
        expect(wrapper.html()).toContain('progressspinner-stub');
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
});
