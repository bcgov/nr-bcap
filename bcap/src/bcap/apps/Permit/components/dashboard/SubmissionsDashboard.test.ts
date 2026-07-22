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

const fetchDrafts = vi.fn();
const fetchMyProjects = vi.fn();
const deleteDraft = vi.fn();
vi.mock('@/bcap/apps/Permit/api.ts', () => ({
    fetchDrafts: (...args: unknown[]) => fetchDrafts(...args),
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

function makeDraft(overrides: Record<string, unknown> = {}) {
    return {
        id: 'draft-1',
        graph_slug: 'permit_application',
        created: '2026-03-01T00:00:00Z',
        updated: '2026-03-02T00:00:00Z',
        data: {
            application_identification: {
                aliased_data: {
                    project_name: {
                        node_value: { en: { value: 'Draft One' } },
                    },
                },
            },
        },
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
    fetchDrafts.mockReset().mockResolvedValue([]);
    fetchMyProjects.mockReset().mockResolvedValue([]);
    deleteDraft.mockReset().mockResolvedValue(undefined);
    push.mockReset();
});

afterEach(() => {
    vi.restoreAllMocks();
});

describe('data loading', () => {
    it('shows the spinner until both requests resolve', async () => {
        fetchDrafts.mockReturnValue(new Promise(() => {}));
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
    it('shows only permit application drafts', async () => {
        fetchDrafts.mockResolvedValue([
            makeDraft(),
            makeDraft({ id: 'draft-2', graph_slug: 'investigation' }),
        ]);
        const wrapper = await mountDashboard();

        const labels = wrapper
            .findAllComponents(CardStub)
            // The first Card is the "start a new workflow" tile.
            .slice(1)
            .map((card) => card.props('label'));
        expect(labels).toEqual(['Draft One']);
    });

    it('opens the confirmation dialog from the delete button', async () => {
        fetchDrafts.mockResolvedValue([makeDraft()]);
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
        fetchDrafts.mockResolvedValue([makeDraft()]);

        const wrapper = await mountDashboard();

        expect(wrapper.findAll('.draft-card-wrapper')).toHaveLength(1);
    });
});
