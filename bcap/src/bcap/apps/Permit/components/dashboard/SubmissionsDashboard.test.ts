import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { defineComponent } from 'vue';
import { mount, flushPromises } from '@vue/test-utils';

const push = vi.fn();
vi.mock('vue-router', () => ({
    useRouter: () => ({ push }),
}));

vi.mock('@/bcap/apps/Permit/routes.ts', () => ({
    routeNames: {
        baseModule: 'baseModule',
        investigationModule: 'investigationModule',
        permitDetails: 'permitDetails',
    },
}));

const fetchDraftCards = vi.fn();
const fetchMyProjects = vi.fn();
const deleteDraft = vi.fn();
vi.mock('@/bcap/apps/Permit/api.ts', () => ({
    fetchDraftCards: (...args: unknown[]) => fetchDraftCards(...args),
    fetchMyProjects: (...args: unknown[]) => fetchMyProjects(...args),
    deleteDraft: (...args: unknown[]) => deleteDraft(...args),
}));

vi.mock('vue3-gettext', () => ({
    useGettext: () => ({ $gettext: (text: string) => text }),
}));

vi.mock('arches', () => ({
    default: { urls: { plugin: (slug: string) => `/plugins/${slug}` } },
}));

import SubmissionsDashboard from './SubmissionsDashboard.vue';

// Stand-in for ProjectCard so the props the dashboard computes are inspectable.
const ProjectCardStub = defineComponent({
    name: 'ProjectCard',
    props: {
        bodyTitle: { type: String, default: '' },
        bodySubtitle1: { type: String, default: '' },
        bodySubtitle2: { type: String, default: '' },
        capLabel: { type: String, default: '' },
        capDate: { type: String, default: '' },
        capPriority: { type: Boolean, default: false },
        body1: { type: String, default: '' },
        body2: { type: String, default: '' },
        body3: { type: String, default: '' },
        footerName: { type: String, default: '' },
        footerDate: { type: String, default: '' },
        unreadMessages: { type: Number, default: 0 },
        route: { type: Object, default: () => ({}) },
    },
    template: '<div class="project-card-stub">{{ bodyTitle }}</div>',
});

const CardStub = defineComponent({
    name: 'CenterCard',
    props: {
        label: { type: String, default: '' },
        description: { type: String, default: '' },
        subtitle: { type: String, default: '' },
        route: { type: Object, default: () => ({}) },
    },
    template: '<div class="center-card-stub">{{ label }}</div>',
});

// Panel/Fluid render nothing useful here but must pass their slots through.
const PassThrough = { template: '<div><slot /></div>' };

// Declares `visible` so the test can read it; the auto-stub does not.
const DialogStub = defineComponent({
    name: 'DeleteDialog',
    props: { visible: { type: Boolean, default: false } },
    template: '<div class="dialog-stub"></div>',
});

function makeProject(overrides: Record<string, unknown> = {}) {
    return {
        id: 'res-1',
        is_draft: false,
        status: 'Under Review',
        created_by_name: 'testuser',
        created_date: '2026-03-04T00:00:00Z',
        project_name: 'My Project',
        application_number: 'APP-123',
        submission_type: 'Site Visit',
        industrial_sector: 'Mining',
        permit_id: null,
        permit_number: 'PN-9',
        urgency: 5,
        priority_level: 'High',
        unread_messages: 0,
        module_progress: {
            current_module: 'Permit Review',
            completed: 1,
            total: 3,
        },
        ...overrides,
    };
}

// A draft card as the external dashboard returns it.
function makeDraft(overrides: Record<string, unknown> = {}) {
    return {
        id: 'draft-1',
        is_draft: true,
        graph_slug: 'permit_application',
        permit_application_id: '',
        application_number: 'APP-1',
        status: 'Submission Required',
        project_name: 'Draft One',
        submission_type: 'Permit Application - Standard',
        created_by_name: 'Test User',
        created_date: '2026-03-01T00:00:00Z',
        updated_date: '2026-03-02T00:00:00Z',
        unread_messages: 0,
        ...overrides,
    };
}

const STUBS = {
    ProjectCard: ProjectCardStub,
    Card: CardStub,
    Panel: PassThrough,
    Fluid: PassThrough,
    Dialog: DialogStub,
    Button: true,
    SortingBar: true,
    ProgressSpinner: true,
};

async function mountDashboard() {
    const wrapper = mount(SubmissionsDashboard, { global: { stubs: STUBS } });
    await flushPromises();
    return wrapper;
}

async function switchTab(
    wrapper: Awaited<ReturnType<typeof mountDashboard>>,
    tab: string,
) {
    wrapper
        .findComponent({ name: 'SortingBar' })
        .vm.$emit('update:activeTab', tab);
    await flushPromises();
}

beforeEach(() => {
    localStorage.clear();
    fetchDraftCards.mockReset().mockResolvedValue([]);
    fetchMyProjects.mockReset().mockResolvedValue([]);
    deleteDraft.mockReset().mockResolvedValue(undefined);
    push.mockReset();
});

afterEach(() => {
    vi.restoreAllMocks();
});

describe('data loading', () => {
    it('shows the spinner until both requests resolve', async () => {
        fetchDraftCards.mockReturnValue(new Promise(() => {}));
        const wrapper = mount(SubmissionsDashboard, {
            global: { stubs: STUBS },
        });
        await flushPromises();

        expect(wrapper.find('.loading-state').exists()).toBe(true);
        expect(wrapper.find('.tab-content-container').exists()).toBe(false);
    });

    it('clears the spinner when a request fails', async () => {
        fetchMyProjects.mockRejectedValue(new Error('boom'));
        vi.spyOn(console, 'error').mockImplementation(() => {});

        const wrapper = await mountDashboard();

        expect(wrapper.find('.loading-state').exists()).toBe(false);
        expect(wrapper.find('.tab-content-container').exists()).toBe(true);
    });
});

describe('project cards', () => {
    it('maps a submitted project onto the card props', async () => {
        fetchMyProjects.mockResolvedValue([makeProject()]);
        const wrapper = await mountDashboard();
        await switchTab(wrapper, 'my_projects');

        const card = wrapper.findComponent(ProjectCardStub);
        expect(card.props('bodyTitle')).toBe('My Project');
        expect(card.props('bodySubtitle1')).toBe('APP-123');
        expect(card.props('bodySubtitle2')).toBe('Mining');
        expect(card.props('capLabel')).toBe('Under Review');
        expect(card.props('capPriority')).toBe(true);
        expect(card.props('footerName')).toBe('testuser');
    });

    it('labels the submission type, permit and module progress', async () => {
        fetchMyProjects.mockResolvedValue([makeProject()]);
        const wrapper = await mountDashboard();
        await switchTab(wrapper, 'my_projects');

        const card = wrapper.findComponent(ProjectCardStub);
        expect(card.props('body1')).toBe('Type: Site Visit');
        expect(card.props('body2')).toBe('Permit: PN-9');
        expect(card.props('body3')).toContain('1/3 modules complete');
    });

    it('omits the type and permit lines when the values are missing', async () => {
        fetchMyProjects.mockResolvedValue([
            makeProject({ submission_type: '', permit_number: '' }),
        ]);
        const wrapper = await mountDashboard();
        await switchTab(wrapper, 'my_projects');

        const card = wrapper.findComponent(ProjectCardStub);
        expect(card.props('body1')).toBe('');
        expect(card.props('body2')).toBe('');
    });

    it('routes to the permit details view on click', async () => {
        fetchMyProjects.mockResolvedValue([makeProject()]);
        const wrapper = await mountDashboard();
        await switchTab(wrapper, 'my_projects');

        await wrapper.findComponent(ProjectCardStub).trigger('click');

        expect(push).toHaveBeenCalledWith({
            name: 'permitDetails',
            params: { id: 'res-1' },
        });
    });

    it('filters projects by the search query', async () => {
        fetchMyProjects.mockResolvedValue([
            makeProject({ id: 'a', project_name: 'Bridge Survey' }),
            makeProject({ id: 'b', project_name: 'Quarry Dig' }),
        ]);
        const wrapper = await mountDashboard();
        await switchTab(wrapper, 'my_projects');

        wrapper
            .findComponent({ name: 'SortingBar' })
            .vm.$emit('update:search', 'quarry');
        await flushPromises();

        const titles = wrapper
            .findAllComponents(ProjectCardStub)
            .map((card) => card.props('bodyTitle'));
        expect(titles).toEqual(['Quarry Dig']);
    });
});

describe('drafts', () => {
    it('labels each draft card with its project name and filing type', async () => {
        fetchDraftCards.mockResolvedValue([
            makeDraft(),
            makeDraft({ id: 'draft-2', project_name: 'Draft Two' }),
        ]);
        const wrapper = await mountDashboard();

        const cards = wrapper.findAllComponents(ProjectCardStub);
        expect(cards.map((card) => card.props('bodyTitle'))).toEqual([
            'Draft One',
            'Draft Two',
        ]);
        // The filing type comes off the card, not a static draft label.
        expect(cards[0].props('body1')).toBe(
            'Type: Permit Application - Standard',
        );
    });

    it('shows the unread message count on a draft card', async () => {
        fetchDraftCards.mockResolvedValue([makeDraft({ unread_messages: 3 })]);
        const wrapper = await mountDashboard();

        expect(
            wrapper.findComponent(ProjectCardStub).props('unreadMessages'),
        ).toBe(3);
    });

    it('names and resumes a module draft through its own workflow', async () => {
        fetchDraftCards.mockResolvedValue([
            makeDraft({
                id: 'draft-3',
                graph_slug: 'investigation',
                project_name: '',
                submission_type: '',
            }),
        ]);
        const wrapper = await mountDashboard();

        const card = wrapper.findComponent(ProjectCardStub);
        expect(card.props('bodyTitle')).toBe('Investigation');
        expect(card.props('body1')).toBe('Type: Investigation Draft');
        // The permit it hangs off, so the card says what it belongs to.
        expect(card.props('bodySubtitle1')).toBe('APP-1');
        expect(card.props('route')).toEqual({
            name: 'investigationModule',
            query: { draftId: 'draft-3' },
        });
    });

    it('still names the module when the card carries its permit details', async () => {
        fetchDraftCards.mockResolvedValue([
            makeDraft({
                id: 'draft-4',
                graph_slug: 'investigation',
                permit_application_id: 'permit-1',
                // Both inherited from the parent permit application.
                project_name: 'Big Project',
                submission_type: 'Permit Application - Standard',
            }),
        ]);
        const wrapper = await mountDashboard();

        const card = wrapper.findComponent(ProjectCardStub);
        expect(card.props('bodyTitle')).toBe('Investigation');
        expect(card.props('body1')).toBe('Type: Investigation Draft');
        // The permit exists, so the card opens its filing summary with the
        // draft's own section expanded.
        expect(card.props('route')).toEqual({
            name: 'permitDetails',
            params: { id: 'permit-1' },
            query: { draft: 'draft-4' },
        });
    });

    it('opens the confirmation dialog from the delete button', async () => {
        fetchDraftCards.mockResolvedValue([makeDraft()]);
        const wrapper = await mountDashboard();

        await wrapper.find('.draft-delete-btn').trigger('click');

        expect(wrapper.findComponent(DialogStub).props('visible')).toBe(true);
        // Opening the dialog must not delete anything on its own.
        expect(deleteDraft).not.toHaveBeenCalled();
    });
});

describe('tab persistence', () => {
    it('starts on drafts and remembers the chosen tab', async () => {
        const wrapper = await mountDashboard();
        await switchTab(wrapper, 'my_projects');

        expect(localStorage.getItem('bcap.externalDashboard.tab')).toBe(
            'my_projects',
        );
    });

    it('restores a stored tab on mount', async () => {
        localStorage.setItem('bcap.externalDashboard.tab', 'my_projects');
        fetchMyProjects.mockResolvedValue([makeProject()]);

        const wrapper = await mountDashboard();

        expect(wrapper.findComponent(ProjectCardStub).exists()).toBe(true);
    });

    it('ignores an unrecognised stored tab', async () => {
        localStorage.setItem('bcap.externalDashboard.tab', 'nonsense');
        fetchDraftCards.mockResolvedValue([makeDraft()]);

        const wrapper = await mountDashboard();

        expect(wrapper.findAll('.draft-card-wrapper')).toHaveLength(1);
    });
});
