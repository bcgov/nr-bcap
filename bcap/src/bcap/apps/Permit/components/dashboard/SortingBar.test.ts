import { describe, it, expect, vi } from 'vitest';
import { defineComponent } from 'vue';
import { mount } from '@vue/test-utils';

import SortingBar from './SortingBar.vue';

// PrimeVue's Button reads plugin config no test installs, and its Menu is a
// popup; both stand in as plain elements so clicks and the menu model are
// readable.
const ButtonStub = defineComponent({
    name: 'ButtonStub',
    inheritAttrs: false,
    template: '<button v-bind="$attrs"><slot /></button>',
});

const MenuStub = defineComponent({
    name: 'MenuStub',
    props: { model: { type: Array, default: () => [] } },
    methods: { toggle: vi.fn() },
    template: '<div class="menu-stub"></div>',
});

type MenuItem = { label: string; icon: string; class: string; command(): void };

const SORT_OPTIONS = [
    { label: 'Default', value: 'default' },
    { label: 'Name', value: 'name' },
    { label: 'Cap date', value: 'capDate' },
    { label: 'Footer date', value: 'footerDate' },
];

function mountBar(props: Record<string, unknown> = {}) {
    return mount(SortingBar, {
        props: {
            sortOptions: SORT_OPTIONS,
            lastUpdated: new Date('2026-03-04T10:30:00Z'),
            ...props,
        },
        global: { stubs: { Button: ButtonStub, Menu: MenuStub } },
    });
}

const sortItems = (wrapper: ReturnType<typeof mountBar>) =>
    wrapper.findComponent(MenuStub).props('model') as MenuItem[];

const itemFor = (wrapper: ReturnType<typeof mountBar>, label: string) =>
    sortItems(wrapper).find((item) => item.label === label) as MenuItem;

const chipLabels = (wrapper: ReturnType<typeof mountBar>) =>
    wrapper.findAll('.filter-chip').map((chip) => chip.text());

describe('tabs', () => {
    it('marks the active segment and emits the one clicked', async () => {
        const wrapper = mountBar({
            tabs: [
                { label: 'Mine', value: 'mine' },
                { label: 'Theirs', value: 'theirs' },
            ],
            activeTab: 'mine',
        });

        const segments = wrapper.findAll('.segment-btn');
        expect(segments.map((s) => s.text())).toEqual(['Mine', 'Theirs']);
        expect(segments[0].classes()).toContain('active');
        expect(segments[1].classes()).not.toContain('active');

        await segments[1].trigger('click');

        expect(wrapper.emitted('update:activeTab')).toEqual([['theirs']]);
    });
});

describe('search', () => {
    it('emits the query, chips it, and clears it from the chip', async () => {
        const wrapper = mountBar();
        await wrapper.find('.search-input').setValue('quarry');

        expect(wrapper.emitted('update:search')).toEqual([['quarry']]);
        expect(chipLabels(wrapper)).toEqual(['Search: quarry']);

        await wrapper.find('.filter-chip').trigger('click');

        expect(
            wrapper.find<HTMLInputElement>('.search-input').element.value,
        ).toBe('');
        expect(wrapper.emitted('update:search')).toEqual([['quarry'], ['']]);
        expect(chipLabels(wrapper)).toEqual([]);
    });
});

describe('messages-only filter', () => {
    it('is left out without a label', () => {
        expect(mountBar().find('.messages-filter').exists()).toBe(false);
    });

    it('emits the checkbox state', async () => {
        const wrapper = mountBar({ messagesOnlyLabel: 'Unread only' });

        await wrapper.find('.messages-filter input').setValue(true);

        expect(wrapper.emitted('update:messagesOnly')).toEqual([[true]]);
    });

    it('chips the filter while it is on and clears it back off', async () => {
        const wrapper = mountBar({
            messagesOnlyLabel: 'Unread only',
            messagesOnly: true,
        });

        expect(chipLabels(wrapper)).toEqual(['Unread only']);

        await wrapper.find('.filter-chip').trigger('click');

        expect(wrapper.emitted('update:messagesOnly')).toEqual([[false]]);
    });
});

describe('sort menu', () => {
    it('flips the order when the active sort is picked again', () => {
        const wrapper = mountBar({ currentSort: 'name', sortOrder: 'asc' });

        itemFor(wrapper, 'Name').command();

        expect(wrapper.emitted('update:sortOrder')).toEqual([['desc']]);
        // Switching sort is what changes the sort key; this only reorders.
        expect(wrapper.emitted('update:currentSort')).toBeUndefined();
        expect(wrapper.emitted('refresh')).toHaveLength(1);
    });

    it('defaults the date-like sorts to newest first', () => {
        for (const label of ['Default', 'Cap date', 'Footer date']) {
            const wrapper = mountBar({ currentSort: 'name', sortOrder: 'asc' });

            itemFor(wrapper, label).command();

            expect(wrapper.emitted('update:sortOrder')).toEqual([['desc']]);
        }
    });

    it('defaults every other sort to ascending', () => {
        const wrapper = mountBar({ currentSort: 'default', sortOrder: 'desc' });

        itemFor(wrapper, 'Name').command();

        expect(wrapper.emitted('update:currentSort')).toEqual([['name']]);
        expect(wrapper.emitted('update:sortOrder')).toEqual([['asc']]);
    });

    it('chips a non-default sort and clears it back to default', async () => {
        const wrapper = mountBar({ currentSort: 'name' });

        expect(chipLabels(wrapper)).toEqual(['Sort: Name']);
        expect(wrapper.find('.sort-btn').text()).toContain('Sort: Name');
        expect(chipLabels(mountBar({ currentSort: 'default' }))).toEqual([]);

        await wrapper.find('.filter-chip').trigger('click');

        expect(wrapper.emitted('update:currentSort')).toEqual([['default']]);
    });
});

describe('results summary', () => {
    it('reports how many of the total are shown, and hides when empty', () => {
        expect(
            mountBar({ shown: 2, total: 5 }).find('.results-summary').text(),
        ).toMatch(/Showing\s*2\s*of\s*5/);
        expect(
            mountBar({ shown: 0, total: 0 }).find('.results-summary').exists(),
        ).toBe(false);
    });
});

describe('refresh', () => {
    it('emits refresh from the button', async () => {
        const wrapper = mountBar();

        await wrapper.find('.refresh-btn').trigger('click');

        expect(wrapper.emitted('refresh')).toHaveLength(1);
    });
});
