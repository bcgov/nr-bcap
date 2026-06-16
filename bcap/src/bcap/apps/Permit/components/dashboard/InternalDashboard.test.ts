import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { defineComponent } from 'vue';
import { mount, flushPromises } from '@vue/test-utils';

// Route is read for ProjectCard navigation; name becomes the card route
vi.mock('vue-router', () => ({
    useRoute: () => ({ name: 'Home', query: {} }),
}));

// The dashboard data source is mocked so we control exactly what renders
const getInternalDashboardData = vi.fn();
vi.mock('@/bcap/components/pages/api.ts', () => ({
    getInternalDashboardData: (...args: unknown[]) =>
        getInternalDashboardData(...args),
}));

// arches.urls.plugin() builds the checklist URL navigateToReport opens
vi.mock('arches', () => ({
    default: {
        urls: {
            plugin: (slug: string) => `/plugins/${slug}`,
        },
    },
}));

import InternalDashboard from './InternalDashboard.vue';

// Stand-in for ProjectCard so we can inspect the props it receives
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

function mountDashboard() {
    return mount(InternalDashboard, {
        global: {
            stubs: {
                ProjectCard: ProjectCardStub,
                SortingBar: true,
            },
        },
    });
}

// Drive a toolbar emit (filter, search, sort, refresh) and wait for the render
async function emitFromToolbar(
    wrapper: ReturnType<typeof mountDashboard>,
    event: string,
    payload?: unknown,
) {
    wrapper.findComponent({ name: 'SortingBar' }).vm.$emit(event, payload);
    await flushPromises();
}

function makeCard(overrides: Record<string, unknown> = {}) {
    return {
        id: 'res-1',
        requirement_id: 'req-1',
        priority_level: 'High',
        requirement_name: 'Site Visit',
        requirement_due_date: '2026-07-01',
        project_name: 'My Project',
        application_number: 'APP-123',
        industrial_sector: 'Mining',
        permit_number: 'PN-9',
        permit_holder: 'Acme Co',
        project_officer: 'Jane Officer',
        ministry_assignee_name: 'John Doe',
        urgency: 5,
        ...overrides,
    };
}

beforeEach(() => {
    getInternalDashboardData.mockReset();
});

afterEach(() => {
    vi.restoreAllMocks();
});

describe('data loading', () => {
    it('shows the loading spinner before data resolves', () => {
        getInternalDashboardData.mockReturnValue(new Promise(() => {}));
        const wrapper = mountDashboard();
        expect(wrapper.find('.loading-state').exists()).toBe(true);
        expect(wrapper.find('.dash-row').exists()).toBe(false);
    });

    it('requests "my_projects" on mount (not the unassigned feed)', async () => {
        getInternalDashboardData.mockResolvedValue([]);
        mountDashboard();
        await flushPromises();
        expect(getInternalDashboardData).toHaveBeenCalledWith(
            'ASSIGNED_TO_ME',
            1,
            100,
        );
    });

    it('renders one ProjectCard per assigned result once loaded', async () => {
        getInternalDashboardData.mockResolvedValue([
            makeCard({ id: 'res-1', project_name: 'Alpha' }),
            makeCard({ id: 'res-2', project_name: 'Beta' }),
        ]);
        const wrapper = mountDashboard();
        await flushPromises();

        expect(wrapper.find('.loading-state').exists()).toBe(false);
        const cards = wrapper.findAllComponents(ProjectCardStub);
        expect(cards).toHaveLength(2);
        expect(cards.map((c) => c.props('bodyTitle'))).toEqual([
            'Alpha',
            'Beta',
        ]);
    });

    it('shows the empty state when no projects match', async () => {
        getInternalDashboardData.mockResolvedValue([]);
        const wrapper = mountDashboard();
        await flushPromises();

        expect(wrapper.findAllComponents(ProjectCardStub)).toHaveLength(0);
        expect(wrapper.find('.empty-state').text()).toContain(
            'No projects match your search criteria.',
        );
    });

    it('hides the spinner and recovers when the API rejects', async () => {
        vi.spyOn(console, 'error').mockImplementation(() => {});
        getInternalDashboardData.mockRejectedValue(new Error('boom'));
        const wrapper = mountDashboard();
        await flushPromises();

        expect(wrapper.find('.loading-state').exists()).toBe(false);
        expect(wrapper.findAllComponents(ProjectCardStub)).toHaveLength(0);
    });
});

describe('field mapping (data shows up right)', () => {
    it('maps backend fields onto the card props', async () => {
        getInternalDashboardData.mockResolvedValue([makeCard()]);
        const wrapper = mountDashboard();
        await flushPromises();

        const card = wrapper.findComponent(ProjectCardStub);
        expect(card.props('bodyTitle')).toBe('My Project');
        expect(card.props('bodySubtitle1')).toBe('APP-123');
        expect(card.props('bodySubtitle2')).toBe('Mining');
        expect(card.props('capLabel')).toBe('Site Visit');
        expect(card.props('capDate')).toBe('2026-07-01');
        expect(card.props('capPriority')).toBe(true);
        expect(card.props('footerName')).toBe('John Doe');
    });

    it('marks capPriority false for non-High priority levels', async () => {
        getInternalDashboardData.mockResolvedValue([
            makeCard({ priority_level: 'Low' }),
        ]);
        const wrapper = mountDashboard();
        await flushPromises();

        expect(
            wrapper.findComponent(ProjectCardStub).props('capPriority'),
        ).toBe(false);
    });

    it('formats labelled body lines as bold-prefixed HTML', async () => {
        getInternalDashboardData.mockResolvedValue([makeCard()]);
        const wrapper = mountDashboard();
        await flushPromises();

        const card = wrapper.findComponent(ProjectCardStub);
        expect(card.props('body1')).toBe('<strong>Permit:</strong> PN-9');
        expect(card.props('body2')).toBe('<strong>Holder:</strong> Acme Co');
        expect(card.props('body3')).toBe(
            '<strong>Officer:</strong> Jane Officer',
        );
    });

    it('falls back to placeholder text for missing fields', async () => {
        getInternalDashboardData.mockResolvedValue([
            {
                id: 'res-x',
                ministry_assignee_name: 'John Doe',
                urgency: 0,
            },
        ]);
        const wrapper = mountDashboard();
        await flushPromises();

        const card = wrapper.findComponent(ProjectCardStub);
        expect(card.props('bodyTitle')).toBe('Unknown Project');
        expect(card.props('bodySubtitle1')).toBe('No App #');
        expect(card.props('capDate')).toBe('Pending');
    });
});

describe('default "my_projects" filter', () => {
    it('renders every card the backend returns (filtering is server-side)', async () => {
        getInternalDashboardData.mockResolvedValue([
            makeCard({ id: 'mine', ministry_assignee_name: 'John Doe' }),
            makeCard({ id: 'theirs', ministry_assignee_name: 'Someone Else' }),
        ]);
        const wrapper = mountDashboard();
        await flushPromises();

        // The ASSIGNED_TO_ME backend filter decides who shows; the component
        // does not re-filter by assignee on the client.
        const cards = wrapper.findAllComponents(ProjectCardStub);
        expect(cards).toHaveLength(2);
    });

    it('counts all returned cards in the results summary', async () => {
        getInternalDashboardData.mockResolvedValue([
            makeCard({ id: 'mine' }),
            makeCard({ id: 'theirs' }),
        ]);
        const wrapper = mountDashboard();
        await flushPromises();

        const summary = wrapper.find('.results-summary').text();
        expect(summary).toContain('Showing');
        expect(summary).toMatch(/2[\s\S]*of[\s\S]*2/);
    });
});

describe('filter switching', () => {
    it('reloads from the unassigned feed when that tab is selected', async () => {
        getInternalDashboardData.mockResolvedValue([
            makeCard({ id: 'u1', ministry_assignee_name: undefined }),
        ]);
        const wrapper = mountDashboard();
        await flushPromises();
        getInternalDashboardData.mockClear();

        await emitFromToolbar(wrapper, 'update:activeTab', 'UNASSIGNED');

        // The status passed to the feed switches to the unassigned filter.
        expect(getInternalDashboardData).toHaveBeenCalledWith(
            'UNASSIGNED',
            1,
            100,
        );
        const cards = wrapper.findAllComponents(ProjectCardStub);
        expect(cards).toHaveLength(1);
        expect(cards[0].props('footerName')).toBe('Unassigned');
    });

    it('does not reload when the active tab is unchanged', async () => {
        getInternalDashboardData.mockResolvedValue([]);
        const wrapper = mountDashboard();
        await flushPromises();
        getInternalDashboardData.mockClear();

        await emitFromToolbar(wrapper, 'update:activeTab', 'ASSIGNED_TO_ME');

        expect(getInternalDashboardData).not.toHaveBeenCalled();
    });

    it('shows every result under a non-assignee filter', async () => {
        getInternalDashboardData.mockResolvedValue([
            makeCard({ id: 'a', ministry_assignee_name: 'John Doe' }),
            makeCard({ id: 'b', ministry_assignee_name: 'Someone Else' }),
        ]);
        const wrapper = mountDashboard();
        await flushPromises();

        await emitFromToolbar(wrapper, 'update:activeTab', 'ALL');

        expect(wrapper.findAllComponents(ProjectCardStub)).toHaveLength(2);
    });

    it('reloads when the toolbar requests a refresh', async () => {
        getInternalDashboardData.mockResolvedValue([]);
        const wrapper = mountDashboard();
        await flushPromises();
        getInternalDashboardData.mockClear();

        await emitFromToolbar(wrapper, 'refresh');

        expect(getInternalDashboardData).toHaveBeenCalledWith(
            'ASSIGNED_TO_ME',
            1,
            100,
        );
    });
});

describe('search filtering', () => {
    it('keeps only cards whose title matches the search term', async () => {
        getInternalDashboardData.mockResolvedValue([
            makeCard({ id: 'a', project_name: 'Copper Mine' }),
            makeCard({ id: 'b', project_name: 'Gravel Pit' }),
        ]);
        const wrapper = mountDashboard();
        await flushPromises();

        await emitFromToolbar(wrapper, 'update:search', 'copper');

        const cards = wrapper.findAllComponents(ProjectCardStub);
        expect(cards).toHaveLength(1);
        expect(cards[0].props('bodyTitle')).toBe('Copper Mine');
    });

    it('matches against any mapped body field (e.g. permit holder)', async () => {
        getInternalDashboardData.mockResolvedValue([
            makeCard({ id: 'a', permit_holder: 'Acme Co' }),
            makeCard({ id: 'b', permit_holder: 'Globex' }),
        ]);
        const wrapper = mountDashboard();
        await flushPromises();

        await emitFromToolbar(wrapper, 'update:search', 'acme');

        expect(wrapper.findAllComponents(ProjectCardStub)).toHaveLength(1);
    });

    it('treats "priority" as a keyword surfacing only starred cards', async () => {
        getInternalDashboardData.mockResolvedValue([
            makeCard({ id: 'hi', project_name: 'Zzz', priority_level: 'High' }),
            makeCard({ id: 'lo', project_name: 'Yyy', priority_level: 'Low' }),
        ]);
        const wrapper = mountDashboard();
        await flushPromises();

        await emitFromToolbar(wrapper, 'update:search', 'priority');

        const cards = wrapper.findAllComponents(ProjectCardStub);
        expect(cards).toHaveLength(1);
        expect(cards[0].props('capPriority')).toBe(true);
    });

    it('labels the results summary with the active search term', async () => {
        getInternalDashboardData.mockResolvedValue([makeCard()]);
        const wrapper = mountDashboard();
        await flushPromises();

        await emitFromToolbar(wrapper, 'update:search', 'project');

        expect(wrapper.find('.active-search-label').text()).toContain(
            'filtered by "project"',
        );
    });

    it('shows the empty state when the search matches nothing', async () => {
        getInternalDashboardData.mockResolvedValue([makeCard()]);
        const wrapper = mountDashboard();
        await flushPromises();

        await emitFromToolbar(wrapper, 'update:search', 'no-such-thing');

        expect(wrapper.findAllComponents(ProjectCardStub)).toHaveLength(0);
        expect(wrapper.find('.empty-state').exists()).toBe(true);
    });
});

describe('sorting', () => {
    function titlesOf(wrapper: ReturnType<typeof mountDashboard>) {
        return wrapper
            .findAllComponents(ProjectCardStub)
            .map((c) => c.props('bodyTitle'));
    }

    it('sorts by due date with the oldest first', async () => {
        getInternalDashboardData.mockResolvedValue([
            makeCard({
                id: 'late',
                project_name: 'Late',
                requirement_due_date: '2026-12-01',
            }),
            makeCard({
                id: 'early',
                project_name: 'Early',
                requirement_due_date: '2026-01-01',
            }),
        ]);
        const wrapper = mountDashboard();
        await flushPromises();

        await emitFromToolbar(wrapper, 'update:currentSort', 'capDate');

        expect(titlesOf(wrapper)).toEqual(['Early', 'Late']);
    });

    it('pushes cards with unparseable dates to the end', async () => {
        getInternalDashboardData.mockResolvedValue([
            makeCard({
                id: 'none',
                project_name: 'NoDate',
                requirement_due_date: undefined,
            }),
            makeCard({
                id: 'has',
                project_name: 'HasDate',
                requirement_due_date: '2026-01-01',
            }),
        ]);
        const wrapper = mountDashboard();
        await flushPromises();

        await emitFromToolbar(wrapper, 'update:currentSort', 'capDate');

        expect(titlesOf(wrapper)).toEqual(['HasDate', 'NoDate']);
    });

    it('leaves cards in place when none have a parseable date', async () => {
        getInternalDashboardData.mockResolvedValue([
            makeCard({
                id: 'a',
                project_name: 'First',
                requirement_due_date: undefined,
            }),
            makeCard({
                id: 'b',
                project_name: 'Second',
                requirement_due_date: undefined,
            }),
        ]);
        const wrapper = mountDashboard();
        await flushPromises();

        await emitFromToolbar(wrapper, 'update:currentSort', 'capDate');

        expect(titlesOf(wrapper)).toEqual(['First', 'Second']);
    });

    it('sorts starred cards first when sorting by priority', async () => {
        getInternalDashboardData.mockResolvedValue([
            makeCard({ id: 'lo', project_name: 'Low', priority_level: 'Low' }),
            makeCard({
                id: 'hi',
                project_name: 'High',
                priority_level: 'High',
            }),
        ]);
        const wrapper = mountDashboard();
        await flushPromises();

        await emitFromToolbar(wrapper, 'update:currentSort', 'capPriority');

        expect(titlesOf(wrapper)).toEqual(['High', 'Low']);
    });

    it('sorts alphabetically by a string field', async () => {
        getInternalDashboardData.mockResolvedValue([
            makeCard({
                id: 'b',
                project_name: 'Bee',
                application_number: 'BBB',
            }),
            makeCard({
                id: 'a',
                project_name: 'Ay',
                application_number: 'AAA',
            }),
        ]);
        const wrapper = mountDashboard();
        await flushPromises();

        await emitFromToolbar(wrapper, 'update:currentSort', 'bodySubtitle1');

        expect(titlesOf(wrapper)).toEqual(['Ay', 'Bee']);
    });

    it('reverses the result order when sort order is descending', async () => {
        getInternalDashboardData.mockResolvedValue([
            makeCard({
                id: 'a',
                project_name: 'Ay',
                application_number: 'AAA',
            }),
            makeCard({
                id: 'b',
                project_name: 'Bee',
                application_number: 'BBB',
            }),
        ]);
        const wrapper = mountDashboard();
        await flushPromises();

        await emitFromToolbar(wrapper, 'update:currentSort', 'bodySubtitle1');
        await emitFromToolbar(wrapper, 'update:sortOrder', 'desc');

        expect(titlesOf(wrapper)).toEqual(['Bee', 'Ay']);
    });
});

describe('navigateToReport', () => {
    it('opens the checklist for the clicked card in a named window', async () => {
        const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null);
        getInternalDashboardData.mockResolvedValue([
            makeCard({ id: 'res-1', requirement_id: 'req-1' }),
        ]);
        const wrapper = mountDashboard();
        await flushPromises();

        await wrapper.findComponent(ProjectCardStub).trigger('click');

        expect(openSpy).toHaveBeenCalledWith(
            '/plugins/internal-permit-dashboard/checklist?id=req-1',
            'req-1',
        );
    });

    it('falls back to the resource id when no requirement id is present', async () => {
        const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null);
        getInternalDashboardData.mockResolvedValue([
            makeCard({ id: 'res-9', requirement_id: undefined }),
        ]);
        const wrapper = mountDashboard();
        await flushPromises();

        await wrapper.findComponent(ProjectCardStub).trigger('click');

        expect(openSpy).toHaveBeenCalledWith(
            '/plugins/internal-permit-dashboard/checklist?id=res-9',
            'res-9',
        );
    });
});
