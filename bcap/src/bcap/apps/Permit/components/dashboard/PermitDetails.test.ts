import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import PermitDetails from './PermitDetails.vue';
import {
    fetchPermitDetails,
    patchPermitSubmissionDate,
    fetchDrafts,
    fetchPermitModules,
} from '@/bcap/apps/Permit/api.ts';
import { GraphSlug } from '@/bcap/apps/Permit/graphSlug.ts';
import type { PermitAliasedData } from '@/bcap/types.ts';

// 1. Mock the API Service
vi.mock('@/bcap/apps/Permit/api.ts', () => ({
    fetchPermitDetails: vi.fn(),
    patchPermitSubmissionDate: vi.fn(),
    fetchDrafts: vi.fn(() => Promise.resolve([])),
    fetchPermitModules: vi.fn(() => Promise.resolve([])),
}));

vi.mock('@/bcap/apps/Permit/Modules/ReviewSummary.vue', () => ({
    default: { template: '<div class="mock-review-summary"></div>' },
}));

// 2. Mock Vue Router
const mockPush = vi.fn();
vi.mock('vue-router', () => ({
    useRoute: () => ({
        params: { id: 'mock-permit-123' },
        query: {},
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
        // Default to no investigations; tests that need them override per-case.
        // clearAllMocks resets calls but keeps implementations, so reset here.
        vi.mocked(fetchDrafts).mockResolvedValue([]);
        vi.mocked(fetchPermitModules).mockResolvedValue([]);
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

        // menuItems[1] is the Investigation module (an enabled module); Add
        // navigates to its route with the current permit as the query param.
        expect(mockPush).toHaveBeenCalledWith({
            name: 'investigationModule',
            query: { permitId: 'mock-permit-123' },
        });
    });

    it('fetches drafts and completed modules on mount', async () => {
        vi.mocked(fetchDrafts).mockResolvedValue([
            // This permit's investigation draft -- kept.
            {
                id: 'd1',
                graph_slug: GraphSlug.Investigation,
                data: { parent_resource_id: 'mock-permit-123' },
            },
            // Another permit's draft -- filtered out.
            {
                id: 'd2',
                graph_slug: GraphSlug.Investigation,
                data: { parent_resource_id: 'other-permit' },
            },
        ] as never);
        vi.mocked(fetchPermitModules).mockResolvedValue([
            { id: 'c1', graph_slug: GraphSlug.Investigation, data: {} },
        ] as never);

        const wrapper = mount(PermitDetails, globalMountOptions);
        await flushPromises();

        expect(fetchDrafts).toHaveBeenCalled();
        expect(fetchPermitModules).toHaveBeenCalledWith(
            'mock-permit-123',
            GraphSlug.Investigation,
        );

        const vm = wrapper.vm as unknown as {
            state: {
                investigationDrafts: unknown[];
                completedInvestigations: unknown[];
            };
        };
        // Only the draft belonging to this permit survives the filter.
        expect(vm.state.investigationDrafts).toHaveLength(1);
        expect(vm.state.completedInvestigations).toHaveLength(1);
    });

    it('switches the content when a different module is selected', async () => {
        const wrapper = mount(PermitDetails, globalMountOptions);
        await flushPromises();

        const menuItems = wrapper.findAll('.menu-item');
        // menuItems[2] is Inspection, a "coming soon" (disabled) module.
        await menuItems[2].trigger('click');

        expect(wrapper.find('.content-title').text()).toBe('Inspection module');
        const addBtn = wrapper.find('.add-module-btn');
        expect(addBtn.attributes('disabled')).toBeDefined();
        expect(addBtn.text()).toContain('Coming soon');
    });

    it('offers Site Visit as a disabled "coming soon" module', async () => {
        const wrapper = mount(PermitDetails, globalMountOptions);
        await flushPromises();

        const menuItems = wrapper.findAll('.menu-item');
        await menuItems[menuItems.length - 1].trigger('click');

        expect(wrapper.find('.content-title').text()).toBe('Site Visit module');
        const addBtn = wrapper.find('.add-module-btn');
        expect(addBtn.attributes('disabled')).toBeDefined();
        expect(addBtn.text()).toContain('Coming soon');
    });

    it('refetches investigations when returning to Project Summary', async () => {
        const wrapper = mount(PermitDetails, globalMountOptions);
        await flushPromises();

        vi.mocked(fetchDrafts).mockClear();
        vi.mocked(fetchPermitModules).mockClear();

        const menuItems = wrapper.findAll('.menu-item');
        await menuItems[1].trigger('click');
        expect(fetchDrafts).not.toHaveBeenCalled();

        await menuItems[0].trigger('click');
        await flushPromises();

        expect(fetchDrafts).toHaveBeenCalled();
        expect(fetchPermitModules).toHaveBeenCalledWith(
            'mock-permit-123',
            GraphSlug.Investigation,
        );
    });

    it('shows empty-state messages when the permit has no investigations', async () => {
        const wrapper = mount(PermitDetails, globalMountOptions);
        await flushPromises();

        // The draft/completed lists live under Project Summary (basic-info),
        // which is the default active module on mount.
        const text = wrapper.find('.investigation-lists').text();
        expect(text).toContain('No investigation drafts found.');
        expect(text).toContain('No existing investigations found.');
    });

    it('lists this permit drafts and completed investigations', async () => {
        vi.mocked(fetchDrafts).mockResolvedValue([
            {
                id: 'd1',
                graph_slug: GraphSlug.Investigation,
                data: {
                    parent_resource_id: 'mock-permit-123',
                    investigation_identification: {
                        aliased_data: {
                            investigation_identification: {
                                node_value: { en: { value: 'My Inv' } },
                            },
                        },
                    },
                },
            },
        ] as never);
        vi.mocked(fetchPermitModules).mockResolvedValue([
            {
                id: 'c1',
                graph_slug: GraphSlug.Investigation,
                data: {
                    investigation_identification: {
                        aliased_data: {
                            investigation_identification: {
                                en: { value: 'Done Inv' },
                            },
                        },
                    },
                },
            },
        ] as never);

        const wrapper = mount(PermitDetails, globalMountOptions);
        await flushPromises();

        // Lists render under Project Summary (basic-info), the default module.
        const lists = wrapper.findAll('.investigation-lists .resource-list');
        expect(lists).toHaveLength(2);
        expect(wrapper.find('.investigation-lists').text()).toContain(
            'Investigation Identification: My Inv',
        );
        // Completed investigations link back to the permit resource.
        const completedLink = wrapper.find(
            '.investigation-lists a[href="/bcap/resource/mock-permit-123"]',
        );
        expect(completedLink.text()).toContain('Done Inv');
    });
});
