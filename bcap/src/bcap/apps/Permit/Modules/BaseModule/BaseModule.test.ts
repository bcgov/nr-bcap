import { describe, it, expect, vi, beforeEach } from 'vitest';
import { shallowMount, flushPromises } from '@vue/test-utils';
import BaseModule from './BaseModule.vue';
import { useDraftStore } from '@/bcap/stores/draft.ts';

// Own the submit mock so the date-stamp assertion can read it without a
// top-level import (which Vite resolves before the mock applies).
const { submitApplication } = vi.hoisted(() => ({
    submitApplication: vi.fn(),
}));

vi.mock('@primevue/forms', () => ({
    FormField: { template: '<div />' },
}));

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

vi.mock('vue-router', () => ({
    useRoute: vi.fn(() => ({
        query: {}, // Simulate an empty query (no draftId)
    })),
}));

vi.mock('@/bcap/util.ts', () => ({
    getCsrfToken: vi.fn(() => 'mock-csrf-token'),
}));

vi.mock('arches', () => ({
    default: {
        urls: {
            api_resource_draft: (graphSlug: string) =>
                `/bcap/api/resource_draft/${graphSlug}`,
            plugin: (path: string) => `/${path}`,
        },
    },
}));

vi.mock('@/bcap/apps/Permit/api.ts', async (importOriginal) => ({
    ...(await importOriginal<typeof import('@/bcap/apps/Permit/api.ts')>()),
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
        // With no draftId in the query there is nothing to fetch, so the
        // workflow is ready immediately (the draft is created lazily on first
        // edit, not on mount).
        expect(wrapper.vm.isDataLoaded).toBe(true);
    });

    it('does not create a draft on mount (lazy creation)', async () => {
        shallowMount(BaseModule);

        // Wait for the asynchronous onMounted hook to settle.
        await flushPromises();

        // Nothing is created until the first edit, so an abandoned form leaves
        // no empty draft behind.
        expect(fetch).not.toHaveBeenCalledWith(
            '/bcap/api/resource_draft/permit_application',
            expect.objectContaining({ method: 'POST' }),
        );
    });

    it('offers Site Visit as a disabled related module', () => {
        const wrapper = shallowMount(BaseModule);

        const related = (
            wrapper.vm as unknown as {
                relatedModules: Array<{
                    id: string;
                    label: string;
                    subtitle: string;
                    disabled: boolean;
                }>;
            }
        ).relatedModules;

        const siteVisit = related.find((m) => m.id === 'site-visit');
        expect(siteVisit).toBeDefined();
        expect(siteVisit?.label).toBe('Site Visit');
        expect(siteVisit?.subtitle).toBe('Coming soon');
        expect(siteVisit?.disabled).toBe(true);
    });

    it('links a related module to the permit details for that module', () => {
        const wrapper = shallowMount(BaseModule);

        const link = (
            wrapper.vm as unknown as {
                relatedModuleLink: (id: string) => {
                    query: { module: string };
                };
            }
        ).relatedModuleLink('site-visit');

        // The card routes back to the permit details, pre-selecting the module.
        expect(link.query).toEqual({ module: 'site-visit' });
    });

    it('stamps today as the submission date before submitting', async () => {
        const wrapper = shallowMount(BaseModule);
        await flushPromises();

        // Submit requires an existing draft; simulate one the first edit would
        // have created via the store.
        useDraftStore().loadDraft('mock-draft-id', {});

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
