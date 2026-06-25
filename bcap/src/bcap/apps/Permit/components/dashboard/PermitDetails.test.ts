import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import PermitDetails from './PermitDetails.vue';
import {
    fetchPermitDetails,
    patchPermitSubmissionDate,
} from '@/bcap/apps/Permit/api.ts';
import type { PermitAliasedData } from '@/bcap/util.ts';

// 1. Mock the API Service
vi.mock('@/bcap/apps/Permit/api.ts', () => ({
    fetchPermitDetails: vi.fn(),
    patchPermitSubmissionDate: vi.fn(),
}));

vi.mock('@/bcap/apps/Permit/Modules/ReviewSummary.vue', () => ({
    default: { template: '<div class="mock-review-summary"></div>' },
}));

// 2. Mock Vue Router
const mockPush = vi.fn();
vi.mock('vue-router', () => ({
    useRoute: () => ({
        params: { id: 'mock-permit-123' },
    }),
    useRouter: () => ({
        push: mockPush,
    }),
}));

// 3. Setup Mock Data
const mockPermitData = {
    application_identification: {
        aliased_data: {
            project_name: { display_value: 'Test Project Name' },
            application_id: { display_value: 'APP-001' },
        },
    },
    proposed_project: {
        aliased_data: {
            development_project_details: {
                aliased_data: {
                    industrial_sector: { display_value: 'Forestry' },
                },
            },
        },
    },
    application_admin: {
        tileid: 'mock-tile-123',
        nodegroup: 'mock-nodegroup-123',
        aliased_data: {
            application_submission_date: null,
        },
    },
};

describe('PermitDetails.vue', () => {
    // NEW: Share the exact same stubs across all tests so slots are never dropped!
    const globalMountOptions = {
        global: {
            stubs: {
                Panel: {
                    template:
                        '<div><slot name="header"></slot><slot></slot></div>',
                },
                GenericReviewSummary: true,
            },
        },
    };

    beforeEach(() => {
        vi.clearAllMocks();

        vi.mocked(fetchPermitDetails).mockResolvedValue(
            mockPermitData as unknown as PermitAliasedData,
        );
    });

    it('loads permit details on mount and renders header info', async () => {
        const wrapper = mount(PermitDetails, globalMountOptions);

        await flushPromises();

        expect(fetchPermitDetails).toHaveBeenCalledWith('mock-permit-123');

        expect(wrapper.find('.project-name').text()).toBe('Test Project Name');
        expect(wrapper.find('.application-number').text()).toBe('APP-001');
        expect(wrapper.find('.sector').text()).toBe('Forestry');
    });

    it('calls patchPermitSubmissionDate when the Submit Permit button is clicked', async () => {
        const wrapper = mount(PermitDetails, globalMountOptions);

        await flushPromises();

        // The button will safely exist now!
        const submitBtn = wrapper.find('.print-btn');
        expect(submitBtn.exists()).toBe(true);
        expect(submitBtn.text()).toBe('Submit Permit');

        await submitBtn.trigger('click');
        await flushPromises();

        expect(patchPermitSubmissionDate).toHaveBeenCalledWith(
            'mock-permit-123',
            expect.objectContaining({
                tileid: 'mock-tile-123',
                aliased_data: expect.any(Object),
            }),
        );
    });

    it('navigates to a new module when "Add module" is clicked', async () => {
        const wrapper = mount(PermitDetails, globalMountOptions);

        await flushPromises();

        // The menu items will safely exist now!
        const menuItems = wrapper.findAll('.menu-item');
        await menuItems[1].trigger('click');

        const addBtn = wrapper.find('.add-module-btn');
        await addBtn.trigger('click');

        expect(mockPush).toHaveBeenCalledWith({
            name: 'inspectionModule',
            query: { permitId: 'mock-permit-123' },
        });
    });
});
