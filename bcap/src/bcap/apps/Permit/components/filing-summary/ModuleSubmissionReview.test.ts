import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';

const { fetchResourceData, fetchPermitDetails } = vi.hoisted(() => ({
    fetchResourceData: vi.fn(),
    fetchPermitDetails: vi.fn(),
}));
vi.mock('@/bcap/apps/Permit/api.ts', () => ({
    fetchResourceData,
    fetchPermitDetails,
}));

// The real review pulls in the arches_component_lab widget tree, which vitest
// cannot transform.
vi.mock('@/bcap/apps/Permit/Modules/Step99_Review.vue', () => ({
    default: {
        name: 'Step99_Review',
        props: ['isSubmittedView', 'resourceData'],
        template: '<div class="mock-review" />',
    },
}));

const mockQuery = vi.hoisted(() => ({ value: {} as Record<string, string> }));
const replace = vi.fn();
vi.mock('vue-router', () => ({
    useRoute: () => ({ query: mockQuery.value }),
    useRouter: () => ({ replace }),
}));

import ModuleSubmissionReview from './ModuleSubmissionReview.vue';
import { usePermitHeaderStore } from '@/bcap/stores/permitHeader.ts';

const REVIEW = {
    graph: 'investigation',
    resourceId: 'r-1',
    permitId: 'permit-1',
    title: 'Investigation',
};

const stubs = {
    Panel: {
        template: '<div><slot name="header" /><slot /></div>',
    },
    ProgressSpinner: true,
};

const mountReview = () => mount(ModuleSubmissionReview, { global: { stubs } });

beforeEach(() => {
    vi.clearAllMocks();
    mockQuery.value = {};
    fetchResourceData.mockResolvedValue({ some: 'data' });
    fetchPermitDetails.mockResolvedValue(null);
    vi.spyOn(console, 'error').mockImplementation(() => {});
});

describe('opening cold', () => {
    it('sends the user home when the store has no submission', async () => {
        const wrapper = mountReview();
        await flushPromises();

        expect(replace).toHaveBeenCalledWith({ name: 'root' });
        expect(fetchResourceData).not.toHaveBeenCalled();
        expect(wrapper.findComponent({ name: 'Step99_Review' }).exists()).toBe(
            false,
        );
    });
});

describe('with a submission in the store', () => {
    beforeEach(() => {
        usePermitHeaderStore().setReview(REVIEW);
    });

    it('loads the submission and the permit header', async () => {
        const wrapper = mountReview();
        await flushPromises();

        expect(fetchResourceData).toHaveBeenCalledWith('investigation', 'r-1');
        expect(fetchPermitDetails).toHaveBeenCalledWith('permit-1');
        expect(replace).not.toHaveBeenCalled();
        const review = wrapper.findComponent({ name: 'Step99_Review' });
        expect(review.props('resourceData')).toEqual({ some: 'data' });
        expect(review.props('isSubmittedView')).toBe(true);
    });

    it('titles the page and crumbs back to the permit it belongs to', async () => {
        const wrapper = mountReview();
        await flushPromises();

        expect(wrapper.find('.review-title').text()).toBe(
            'Submission · Investigation',
        );
        expect(wrapper.find('.crumb-link').text()).toBe('Project Summary');
        expect(wrapper.find('.crumb-current').text()).toBe('Investigation');
    });

    it('carries the staff flag back to the permit', async () => {
        mockQuery.value = { staff: 'true' };

        const wrapper = mountReview();
        await flushPromises();

        expect(
            wrapper.findComponent({ name: 'RouterLinkStub' }).props('to'),
        ).toEqual({
            name: 'permitDetails',
            params: { id: 'permit-1' },
            query: { staff: 'true' },
        });
    });

    it('stops the spinner even when the submission fails to load', async () => {
        fetchResourceData.mockRejectedValue(new Error('boom'));

        const wrapper = mountReview();
        await flushPromises();

        expect(wrapper.find('.review-loading').exists()).toBe(false);
        expect(console.error).toHaveBeenCalled();
    });
});
