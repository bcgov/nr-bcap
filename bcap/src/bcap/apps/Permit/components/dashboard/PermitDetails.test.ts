import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import PermitDetails from './PermitDetails.vue';
import {
    fetchPermitDetails,
    patchPermitSubmissionDate,
    fetchDrafts,
} from '@/bcap/apps/Permit/api.ts';
import { GraphSlug } from '@/bcap/apps/Permit/graphSlug.ts';
import type { PermitAliasedData } from '@/bcap/types.ts';

// 1. Mock the API Service
vi.mock('@/bcap/apps/Permit/api.ts', () => ({
    fetchPermitDetails: vi.fn(),
    patchPermitSubmissionDate: vi.fn(),
    fetchDrafts: vi.fn(() => Promise.resolve([])),
    deleteDraft: vi.fn(),
    // Also imported by PermitDetails and its QuestionDialog child; without
    // them the components' error handlers log "Error loading messages/recipients".
    getMessagesForPermit: vi.fn(() =>
        Promise.resolve({ messages: [], threadId: null }),
    ),
    getContributorsForResources: vi.fn(() => Promise.resolve([])),
}));

vi.mock('@/bcap/apps/Permit/Modules/ReviewSummary.vue', () => ({
    default: { template: '<div class="mock-review-summary"></div>' },
}));

// The submitted-modules panel is its own component (covered in its own test);
// stub it so these tests stay focused on PermitDetails and its draft list.
vi.mock('@/bcap/apps/Permit/components/dashboard/CompletedModules.vue', () => ({
    default: {
        props: ['modules', 'permitId', 'isStaff'],
        template:
            '<div class="mock-completed-modules">{{ modules.length }}</div>',
    },
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
        // Default to no drafts; tests that need them override per-case.
        // clearAllMocks resets calls but keeps implementations, so reset here.
        vi.mocked(fetchDrafts).mockResolvedValue([]);
    });

    it('loads permit details on mount and renders header info', async () => {
        const wrapper = mount(PermitDetails, globalMountOptions);

        await flushPromises();

        expect(fetchPermitDetails).toHaveBeenCalledWith('mock-permit-123');

        expect(wrapper.find('.project-name').text()).toBe('Test Project Name');
        // Application id, submission type and sector share one subtitle line.
        expect(wrapper.find('.permit-meta').text()).toBe('APP-001 · Forestry');
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
        await menuItems[2].trigger('click');

        const addBtn = wrapper.find('.add-module-btn');
        await addBtn.trigger('click');

        // menuItems[2] is the Investigation module (an enabled module); Add
        // navigates to its route with the current permit as the query param.
        expect(mockPush).toHaveBeenCalledWith({
            name: 'investigationModule',
            query: { permitId: 'mock-permit-123' },
        });
    });

    it("fetches drafts on mount and keeps only this permit's", async () => {
        vi.mocked(fetchDrafts).mockResolvedValue([
            // This permit's investigation draft -- kept.
            {
                id: 'd1',
                graph_slug: GraphSlug.Investigation,
                parent_resource_id: 'mock-permit-123',
                data: {},
            },
            // Another permit's draft -- filtered out.
            {
                id: 'd2',
                graph_slug: GraphSlug.Investigation,
                parent_resource_id: 'other-permit',
                data: {},
            },
        ] as never);

        const wrapper = mount(PermitDetails, globalMountOptions);
        await flushPromises();

        expect(fetchDrafts).toHaveBeenCalled();

        const vm = wrapper.vm as unknown as {
            state: { investigationDrafts: unknown[] };
        };
        // Only the draft belonging to this permit survives the filter.
        expect(vm.state.investigationDrafts).toHaveLength(1);
    });

    it('switches the content when a different module is selected', async () => {
        const wrapper = mount(PermitDetails, globalMountOptions);
        await flushPromises();

        const menuItems = wrapper.findAll('.menu-item');
        // menuItems[3] is Inspection, a "coming soon" (disabled) module.
        await menuItems[3].trigger('click');

        expect(wrapper.find('.content-title').text()).toBe('Inspection module');
        const addBtn = wrapper.find('.add-module-btn');
        expect(addBtn.attributes('disabled')).toBeDefined();
        expect(addBtn.text()).toContain('Coming soon');
    });

    it('offers Alteration as a disabled "coming soon" module', async () => {
        const wrapper = mount(PermitDetails, globalMountOptions);
        await flushPromises();

        // With no filing type the menu falls back to the permit-application
        // set, which ends at Alteration.
        const menuItems = wrapper.findAll('.menu-item');
        await menuItems[menuItems.length - 1].trigger('click');

        expect(wrapper.find('.content-title').text()).toBe('Alteration module');
        const addBtn = wrapper.find('.add-module-btn');
        expect(addBtn.attributes('disabled')).toBeDefined();
        expect(addBtn.text()).toContain('Coming soon');
    });

    it('reloads drafts when returning to Project Summary', async () => {
        const wrapper = mount(PermitDetails, globalMountOptions);
        await flushPromises();

        vi.mocked(fetchDrafts).mockClear();

        const menuItems = wrapper.findAll('.menu-item');
        // Leaving Project Summary does not reload.
        await menuItems[1].trigger('click');
        expect(fetchDrafts).not.toHaveBeenCalled();

        // Returning to Project Summary reloads the draft list.
        await menuItems[0].trigger('click');
        await flushPromises();
        expect(fetchDrafts).toHaveBeenCalled();
    });

    it('renders no draft panels when the permit has no drafts', async () => {
        const wrapper = mount(PermitDetails, globalMountOptions);
        await flushPromises();

        // The draft section only appears when there are drafts to show.
        expect(wrapper.find('.draft-modules').exists()).toBe(false);
        expect(wrapper.findAll('.draft-panel')).toHaveLength(0);
        // Completed modules are delegated to the stubbed child.
        expect(wrapper.find('.mock-completed-modules').exists()).toBe(true);
    });

    it('lists this permit drafts as accordion panels', async () => {
        vi.mocked(fetchDrafts).mockResolvedValue([
            {
                id: 'd1',
                graph_slug: GraphSlug.Investigation,
                parent_resource_id: 'mock-permit-123',
                data: {
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

        const wrapper = mount(PermitDetails, globalMountOptions);
        await flushPromises();

        const panels = wrapper.findAll('.draft-panel');
        expect(panels).toHaveLength(1);
        expect(wrapper.find('.draft-modules').text()).toContain(
            'Investigation - My Inv',
        );
    });
});
