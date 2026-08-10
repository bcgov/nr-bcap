import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import PermitDetails from './PermitDetails.vue';
import { fetchPermitDetails, fetchDrafts } from '@/bcap/apps/Permit/api.ts';
import { GraphSlug } from '@/bcap/apps/Permit/graphSlug.ts';
import type { PermitApplicationResourceAliasedData } from '@/bcap/client/types.gen.ts';

vi.mock('@/bcap/apps/Permit/api.ts', () => ({
    fetchPermitDetails: vi.fn(),
    fetchDrafts: vi.fn(() => Promise.resolve([])),
    deleteDraft: vi.fn(),
    // Imported by the MessageDialog child; without them its error handlers log
    // "Error loading threads/recipients".
    getThreadsForResource: vi.fn(() => Promise.resolve([])),
    getContributorsForResources: vi.fn(() => Promise.resolve([])),
    // Pulled in by the message store the dialog uses.
    createBcapMessage: vi.fn(),
    markMessageAsRead: vi.fn(),
    setThreadArchived: vi.fn(),
}));

vi.mock('@/bcap/apps/Permit/Modules/ReviewSummary.vue', () => ({
    default: { template: '<div class="mock-review-summary"></div>' },
}));

// The submitted-modules panel is its own component (covered in its own test);
// stub it so these tests stay focused on PermitDetails and its draft list.
vi.mock(
    '@/bcap/apps/Permit/components/filing-summary/modules/ProcessModules.vue',
    () => ({
        default: {
            props: ['modules', 'permitId', 'isStaff'],
            template: '<div class="mock-modules">{{ modules.length }}</div>',
        },
    }),
);

// The query is a ref so a test can open the page the way a
// dashboard card does (?draft=, ?staff=).
const mockPush = vi.fn();
const mockQuery = vi.hoisted(() => ({
    value: {} as Record<string, string>,
}));
vi.mock('vue-router', () => ({
    useRoute: () => ({
        params: { id: 'mock-permit-123' },
        query: mockQuery.value,
    }),
    useRouter: () => ({
        push: mockPush,
    }),
}));

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
    // Shared across all tests so slots are never dropped.
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
        mockQuery.value = {};

        vi.mocked(fetchPermitDetails).mockResolvedValue(
            mockPermitData as unknown as PermitApplicationResourceAliasedData,
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

    it('has no submit action in the header band', async () => {
        const wrapper = mount(PermitDetails, globalMountOptions);

        await flushPromises();

        // Submitting happens in the workflow, not from the permit header.
        expect(wrapper.find('.header-submit-btn').exists()).toBe(false);
    });

    it('navigates to a new module when "Add module" is clicked', async () => {
        const wrapper = mount(PermitDetails, globalMountOptions);

        await flushPromises();

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

    it("fetches this permit's drafts on mount and keeps the investigations", async () => {
        vi.mocked(fetchDrafts).mockResolvedValue([
            // The server returns this permit's drafts; the graph is what still
            // has to be picked apart here.
            {
                id: 'd1',
                graph_slug: GraphSlug.Investigation,
                parent_resource_id: 'mock-permit-123',
                data: {},
            },
            {
                id: 'd2',
                graph_slug: GraphSlug.PermitApplication,
                parent_resource_id: 'mock-permit-123',
                data: {},
            },
        ] as never);

        const wrapper = mount(PermitDetails, globalMountOptions);
        await flushPromises();

        // Filtered by parent in SQL: staff see other users' drafts, so the
        // unfiltered list is every draft in the system.
        expect(fetchDrafts).toHaveBeenCalledWith('mock-permit-123');

        const vm = wrapper.vm as unknown as {
            state: { investigationDrafts: unknown[] };
        };
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
        expect(wrapper.find('.mock-modules').exists()).toBe(true);
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

    describe('draft panels', () => {
        const twoDrafts = () =>
            vi.mocked(fetchDrafts).mockResolvedValue([
                {
                    id: 'd1',
                    graph_slug: GraphSlug.Investigation,
                    parent_resource_id: 'mock-permit-123',
                    data: {},
                },
                {
                    id: 'd2',
                    graph_slug: GraphSlug.Investigation,
                    parent_resource_id: 'mock-permit-123',
                    data: {},
                },
            ] as never);

        type DraftVm = { expandedDrafts: string[] };

        it('pre-expands the draft named on the url, and none without one', async () => {
            twoDrafts();
            mockQuery.value = { draft: 'd2' };

            const wrapper = mount(PermitDetails, globalMountOptions);
            await flushPromises();

            expect((wrapper.vm as unknown as DraftVm).expandedDrafts).toEqual([
                'd2',
            ]);

            mockQuery.value = {};
            const plain = mount(PermitDetails, globalMountOptions);
            await flushPromises();
            expect((plain.vm as unknown as DraftVm).expandedDrafts).toEqual([]);
        });

        it('lets an applicant resume and remove their draft', async () => {
            twoDrafts();

            const wrapper = mount(PermitDetails, globalMountOptions);
            await flushPromises();

            expect(wrapper.find('.draft-resume').text()).toContain(
                'Resume draft',
            );
            expect(wrapper.find('.draft-delete').exists()).toBe(true);
        });

        it('gives staff a read-only draft list', async () => {
            twoDrafts();
            mockQuery.value = { staff: 'true' };

            const wrapper = mount(PermitDetails, globalMountOptions);
            await flushPromises();

            expect(wrapper.find('.draft-resume').text()).toContain(
                'View draft',
            );
            expect(wrapper.find('.draft-delete').exists()).toBe(false);
        });
    });
});
