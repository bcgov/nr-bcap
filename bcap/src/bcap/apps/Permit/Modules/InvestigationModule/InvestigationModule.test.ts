import { describe, it, expect, vi, beforeEach } from 'vitest';
import { shallowMount, flushPromises } from '@vue/test-utils';
import InvestigationModule from './InvestigationModule.vue';
import { useDraftStore } from '@/bcap/stores/draft.ts';
import { GraphSlug } from '@/bcap/apps/Permit/graphSlug.ts';

// Own the api mocks so assertions read them without a top-level import (which
// Vite resolves before the mock applies).
const { submitModule, fetchDraft } = vi.hoisted(() => ({
    submitModule: vi.fn(),
    fetchDraft: vi.fn(),
}));

vi.mock('@/bcap/apps/Permit/api.ts', async (importOriginal) => ({
    ...(await importOriginal<typeof import('@/bcap/apps/Permit/api.ts')>()),
    submitModule,
    fetchDraft,
}));

// Stub the step children (and the shared nav) so the test doesn't transform the
// real arches_component_lab widget tree. shallowMount stubs them at render time;
// mocking the modules also keeps their dependencies out of the transform graph.
const stub = vi.hoisted(() => () => ({ default: { template: '<div />' } }));
vi.mock('./steps/Step1_About.vue', stub);
vi.mock('./steps/Step2_Overview.vue', stub);
vi.mock('./steps/Step3_Personnel.vue', stub);
vi.mock('./steps/Step4_Methods.vue', stub);
vi.mock('./steps/Step5_Recordings.vue', stub);
vi.mock('./steps/Step6_Materials.vue', stub);
vi.mock('./steps/Step7_Remains.vue', stub);
vi.mock('./steps/Step8_Repository.vue', stub);
vi.mock('./steps/Step99_Review.vue', stub);
vi.mock(
    '@/bcgov_arches_common/components/Stepper/components/StepperNavigation/StepperNavigation.vue',
    stub,
);

// The component reads route.query; let each test set it.
const routeQuery = vi.hoisted(() => ({ value: {} as Record<string, string> }));
vi.mock('vue-router', () => ({
    useRoute: () => ({ query: routeQuery.value }),
}));

type ModuleVm = {
    submitNewSiteData: () => Promise<boolean>;
    state: {
        isDataLoaded: boolean;
        finalizedResourceData: unknown;
        submissionErrors: { message: string }[];
    };
};

describe('InvestigationModule.vue', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        routeQuery.value = {};
        vi.spyOn(console, 'error').mockImplementation(() => {});
    });

    it('fetches an existing draft on mount when a draftId is in the query', async () => {
        routeQuery.value = { permitId: 'permit-1', draftId: 'draft-7' };
        fetchDraft.mockResolvedValue({
            id: 'draft-7',
            data: { parent_resource_id: 'permit-1' },
        });

        const wrapper = shallowMount(InvestigationModule);
        await flushPromises();

        expect(fetchDraft).toHaveBeenCalledWith(
            GraphSlug.Investigation,
            'draft-7',
        );
        expect(useDraftStore().draftId).toBe('draft-7');
        expect((wrapper.vm as unknown as ModuleVm).state.isDataLoaded).toBe(
            true,
        );
    });

    it('does not fetch a draft when the query has no draftId', async () => {
        routeQuery.value = { permitId: 'permit-1' };

        const wrapper = shallowMount(InvestigationModule);
        await flushPromises();

        expect(fetchDraft).not.toHaveBeenCalled();
        expect((wrapper.vm as unknown as ModuleVm).state.isDataLoaded).toBe(
            true,
        );
    });

    it('submits the active draft and stores the finalized resource', async () => {
        routeQuery.value = { permitId: 'permit-1' };
        submitModule.mockResolvedValue({ aliased_data: { foo: 'bar' } });

        const wrapper = shallowMount(InvestigationModule);
        await flushPromises();

        // initDraft set the parent permit from the URL; supply a draft id as the
        // first edit would have.
        useDraftStore().loadDraft('draft-7', { x: 1 });

        const vm = wrapper.vm as unknown as ModuleVm;
        const ok = await vm.submitNewSiteData();

        expect(ok).toBe(true);
        expect(submitModule).toHaveBeenCalledWith(
            'permit-1',
            'draft-7',
            GraphSlug.Investigation,
            { x: 1 },
        );
        expect(vm.state.finalizedResourceData).toEqual({
            aliased_data: { foo: 'bar' },
        });
    });

    it('records a submission error when the submit fails', async () => {
        routeQuery.value = { permitId: 'permit-1' };
        submitModule.mockRejectedValue(new Error('nope'));

        const wrapper = shallowMount(InvestigationModule);
        await flushPromises();
        useDraftStore().loadDraft('draft-7', {});

        const vm = wrapper.vm as unknown as ModuleVm;
        const ok = await vm.submitNewSiteData();

        expect(ok).toBe(false);
        expect(submitModule).toHaveBeenCalled();
        expect(vm.state.submissionErrors).toHaveLength(1);
        expect(vm.state.submissionErrors[0].message).toBe('nope');
    });

    it('refuses to submit without an active draft', async () => {
        routeQuery.value = { permitId: 'permit-1' };

        const wrapper = shallowMount(InvestigationModule);
        await flushPromises();

        const vm = wrapper.vm as unknown as ModuleVm;
        const ok = await vm.submitNewSiteData();

        expect(ok).toBe(false);
        expect(submitModule).not.toHaveBeenCalled();
        expect(vm.state.submissionErrors[0].message).toBe(
            'No active draft found.',
        );
    });
});
