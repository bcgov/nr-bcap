import { describe, it, expect, vi, beforeEach } from 'vitest';
import { shallowMount, flushPromises } from '@vue/test-utils';
import WorkflowStepper from './WorkflowStepper.vue';
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

// Stub the shared review and nav so the test doesn't transform the real
// arches_component_lab widget tree.
const stub = vi.hoisted(() => () => ({ default: { template: '<div />' } }));
vi.mock('@/bcap/apps/Permit/Modules/Step99_Review.vue', stub);
vi.mock(
    '@/bcgov_arches_common/components/Stepper/components/StepperNavigation/StepperNavigation.vue',
    stub,
);

// The component reads route.query; let each test set it.
const routeQuery = vi.hoisted(() => ({ value: {} as Record<string, string> }));
const routerPush = vi.fn();
vi.mock('vue-router', () => ({
    useRoute: () => ({ query: routeQuery.value }),
    useRouter: () => ({ push: routerPush }),
}));

const StubStep = { template: '<div />' };
const steps = [
    { label: 'Submission Information', component: StubStep, heading: '' },
    { label: 'Details', component: StubStep },
];

const mountStepper = () =>
    shallowMount(WorkflowStepper, {
        props: {
            graphSlug: GraphSlug.Investigation,
            title: 'Submit Investigation',
            steps,
        },
    });

type StepperVm = {
    submitFiling: () => Promise<boolean>;
    saveAndExit: () => Promise<void>;
    state: {
        isDataLoaded: boolean;
        finalizedResourceData: unknown;
        submissionErrors: { message: string }[];
    };
};

describe('WorkflowStepper.vue', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        routeQuery.value = {};
        vi.spyOn(console, 'error').mockImplementation(() => {});
    });

    it('fetches an existing draft on mount when a draftId is in the query', async () => {
        routeQuery.value = { permitId: 'permit-1', draftId: 'draft-7' };
        fetchDraft.mockResolvedValue({
            id: 'draft-7',
            parent_resource_id: 'permit-1',
            data: {},
        });

        const wrapper = mountStepper();
        await flushPromises();

        expect(fetchDraft).toHaveBeenCalledWith(
            GraphSlug.Investigation,
            'draft-7',
        );
        expect(useDraftStore().draftId).toBe('draft-7');
        expect((wrapper.vm as unknown as StepperVm).state.isDataLoaded).toBe(
            true,
        );
    });

    it('does not fetch a draft when the query has no draftId', async () => {
        routeQuery.value = { permitId: 'permit-1' };

        const wrapper = mountStepper();
        await flushPromises();

        expect(fetchDraft).not.toHaveBeenCalled();
        expect((wrapper.vm as unknown as StepperVm).state.isDataLoaded).toBe(
            true,
        );
    });

    it('submits the active draft and stores the finalized resource', async () => {
        routeQuery.value = { permitId: 'permit-1' };
        submitModule.mockResolvedValue({ aliased_data: { foo: 'bar' } });

        const wrapper = mountStepper();
        await flushPromises();

        // initDraft set the parent permit from the URL; supply a draft id as the
        // first edit would have.
        useDraftStore().loadDraft('draft-7', { x: 1 });

        const vm = wrapper.vm as unknown as StepperVm;
        const ok = await vm.submitFiling();

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

        const wrapper = mountStepper();
        await flushPromises();
        useDraftStore().loadDraft('draft-7', {});

        const vm = wrapper.vm as unknown as StepperVm;
        const ok = await vm.submitFiling();

        expect(ok).toBe(false);
        expect(submitModule).toHaveBeenCalled();
        expect(vm.state.submissionErrors).toHaveLength(1);
        expect(vm.state.submissionErrors[0].message).toBe('nope');
    });

    it('saves the draft and returns to the parent permit on save and exit', async () => {
        routeQuery.value = { permitId: 'permit-1' };

        const wrapper = mountStepper();
        await flushPromises();
        const store = useDraftStore();
        store.loadDraft('draft-7', { x: 1 });
        const saveNow = vi.spyOn(store, 'saveNow').mockResolvedValue();

        await (wrapper.vm as unknown as StepperVm).saveAndExit();

        expect(saveNow).toHaveBeenCalled();
        expect(routerPush).toHaveBeenCalledWith({
            name: 'permitDetails',
            params: { id: 'permit-1' },
        });
    });

    it('exits to the dashboard when the filing has no parent permit', async () => {
        routeQuery.value = {};

        const wrapper = mountStepper();
        await flushPromises();
        vi.spyOn(useDraftStore(), 'saveNow').mockResolvedValue();

        await (wrapper.vm as unknown as StepperVm).saveAndExit();

        expect(routerPush).toHaveBeenCalledWith({ name: 'root' });
    });

    it('refuses to submit without an active draft', async () => {
        routeQuery.value = { permitId: 'permit-1' };

        const wrapper = mountStepper();
        await flushPromises();

        const vm = wrapper.vm as unknown as StepperVm;
        const ok = await vm.submitFiling();

        expect(ok).toBe(false);
        expect(submitModule).not.toHaveBeenCalled();
        expect(vm.state.submissionErrors[0].message).toBe(
            'No active draft found.',
        );
    });
});
