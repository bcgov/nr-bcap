import { shallowMount } from '@vue/test-utils';
import SiteOversight from './SiteOversight.vue';
import WorkflowStepper from '@/bcap/apps/Permit/Modules/WorkflowStepper.vue';

vi.mock('vue-router', () => ({
    useRoute: vi.fn(() => ({ query: {} })),
    useRouter: vi.fn(() => ({ replace: vi.fn() })),
}));

vi.mock('@/bcap/apps/Permit/api.ts', () => ({
    createSectionDraft: vi.fn(),
    fetchWorkflowSession: vi.fn(),
    setRequirementStatus: vi.fn(),
}));

vi.mock('@/bcap/stores/draft.ts', () => ({
    useDraftStore: vi.fn(() => ({
        loadDraft: vi.fn(),
        saveNow: vi.fn(),
    })),
}));

describe('SiteOversight.vue', () => {
    it('renders WorkflowStepper with the HCA permit application graph slug', () => {
        const wrapper = shallowMount(SiteOversight);
        const stepper = wrapper.findComponent(WorkflowStepper);
        expect(stepper.exists()).toBe(true);
        expect(stepper.props('graphSlug')).toBe('hca_permit_application');
    });

    it('passes the correct title to WorkflowStepper', () => {
        const wrapper = shallowMount(SiteOversight);
        const stepper = wrapper.findComponent(WorkflowStepper);
        expect(stepper.props('title')).toBe(
            'HCA Permit Application — Personnel',
        );
    });
});
