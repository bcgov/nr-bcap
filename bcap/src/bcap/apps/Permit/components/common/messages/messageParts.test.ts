import { mount } from '@vue/test-utils';
import { NEW_THREAD_ID } from '@/bcap/types.ts';
import type { FormattedMessage, MessageThread } from '@/bcap/types.ts';
import { useUserStore } from '@/bcap/stores/user.ts';
import { useMessageStore } from '@/bcap/stores/message.ts';
import type { UserResponse } from '@/bcap/client/types.gen.ts';

const { downloadFile } = vi.hoisted(() => ({ downloadFile: vi.fn() }));
vi.mock('@/bcap/util.ts', async (importOriginal) => ({
    ...(await importOriginal<typeof import('@/bcap/util.ts')>()),
    downloadFile,
}));

import MessageHistory from './MessageHistory.vue';
import MessageThreadSidebar from './MessageThreadSidebar.vue';
import MessageAttachmentsField from './MessageAttachmentsField.vue';

let messageCount = 0;
const message = (overrides: Partial<FormattedMessage> = {}) =>
    ({
        id: `m-${++messageCount}`,
        author: 'Hopper, Grace',
        authorIsStaff: false,
        date: '2026-03-04',
        text: 'Please attach the site plan.',
        attachments: [],
        ...overrides,
    }) as FormattedMessage;

const thread = (overrides: Partial<MessageThread> = {}) =>
    ({
        id: 't-1',
        topic: 'Site access',
        startedBy: 'Hopper, Grace',
        lastMessageDate: '2026-03-04T10:00:00',
        isResolved: false,
        onSide: true,
        needsAction: !overrides.isResolved,
        resolvedBy: '',
        resolvedDate: '',
        isInternal: false,
        to: 'Sam Staff',
        ...overrides,
    }) as MessageThread;

beforeEach(() => {
    downloadFile.mockReset();
});

describe('MessageHistory', () => {
    // The history reads the open thread's messages from the store.
    const mountHistory = (messages: FormattedMessage[], isLoading = false) => {
        useMessageStore().openMessages = messages;
        return mount(MessageHistory, { props: { threadId: 't-1', isLoading } });
    };

    it('shows only the loading note while messages are in flight', () => {
        const wrapper = mountHistory([message()], true);

        expect(wrapper.find('.messages-loading').exists()).toBe(true);
        expect(wrapper.find('.historical-message').exists()).toBe(false);
    });

    it('renders each message with its author and text', () => {
        const wrapper = mountHistory([
            message(),
            message({ author: 'Turing, Alan', text: 'Attached.' }),
        ]);

        expect(wrapper.findAll('.historical-message')).toHaveLength(2);
        expect(wrapper.text()).toContain('Hopper, Grace');
        expect(wrapper.text()).toContain('Please attach the site plan.');
    });

    it('marks messages from staff with the Archaeology Branch chip', () => {
        const wrapper = mountHistory([
            message(),
            message({ author: 'Staff, Sam', authorIsStaff: true }),
        ]);

        const [applicant, staff] = wrapper.findAll('.historical-message');
        expect(applicant.find('.staff-chip').exists()).toBe(false);
        expect(staff.find('.staff-chip').text()).toBe('Archaeology Branch');
    });

    it('lists attachments with a human-readable size', () => {
        const wrapper = mountHistory([
            message({
                attachments: [{ url: '/f/1', name: 'plan.pdf', size: 2048 }],
            }),
        ]);

        expect(wrapper.find('.attachment-name').text()).toBe('plan.pdf');
        expect(wrapper.find('.attachment-size').text()).toBe('2 KB');
    });

    it('loads earlier messages only when there are more to load', async () => {
        const wrapper = mountHistory([message()]);
        const store = useMessageStore();
        const loadEarlierMessages = vi
            .spyOn(store, 'loadEarlierMessages')
            .mockResolvedValue();
        expect(wrapper.find('.load-earlier').exists()).toBe(false);

        store.hasEarlierMessages = true;
        await wrapper.vm.$nextTick();
        await wrapper.find('.load-earlier').trigger('click');

        expect(loadEarlierMessages).toHaveBeenCalledWith('t-1');
    });

    it('keeps the scroll position when earlier messages load', async () => {
        const wrapper = mountHistory([message()]);
        const el = wrapper.find('.message-thread').element;
        Object.defineProperty(el, 'scrollHeight', { value: 500 });
        Object.defineProperty(el, 'scrollTop', { value: 0, writable: true });

        const store = useMessageStore();
        store.openMessages = [message(), ...store.openMessages];
        await wrapper.vm.$nextTick();
        expect(el.scrollTop).toBe(0);

        store.openMessages = [...store.openMessages, message()];
        await wrapper.vm.$nextTick();
        expect(el.scrollTop).toBe(500);
    });

    it('downloads through the helper rather than following the link', async () => {
        const wrapper = mountHistory([
            message({
                attachments: [{ url: '/f/1', name: 'plan.pdf', size: 10 }],
            }),
        ]);

        await wrapper.find('.attachment-list a').trigger('click');

        expect(downloadFile).toHaveBeenCalledWith('/f/1', 'plan.pdf');
    });
});

describe('MessageThreadSidebar', () => {
    const mountSidebar = (props: Record<string, unknown> = {}) =>
        mount(MessageThreadSidebar, {
            props: {
                threads: [thread()],
                showArchived: false,
                selectedThreadId: '',
                ...props,
            },
        });

    it('marks the tab matching the archived flag and emits the one picked', async () => {
        const wrapper = mountSidebar();
        const tabs = wrapper.findAll('.sidebar-tab');
        expect(tabs[0].classes()).toContain('active');
        expect(tabs[1].classes()).not.toContain('active');

        await tabs[1].trigger('click');

        expect(wrapper.emitted('select-tab')).toEqual([[true]]);
        expect(
            mountSidebar({ showArchived: true })
                .findAll('.sidebar-tab')[1]
                .classes(),
        ).toContain('active');
    });

    it("flags the selected thread and the viewer's unresolved ones", () => {
        const wrapper = mountSidebar({
            threads: [
                thread({ id: 't-1' }),
                thread({ id: 't-2', isResolved: true }),
                thread({ id: 't-3', needsAction: false }),
            ],
            selectedThreadId: 't-1',
        });

        const items = wrapper.findAll('.thread-list .sidebar-item');
        expect(items[0].classes()).toContain('active');
        expect(items[0].classes()).toContain('unresolved');
        expect(items[1].classes()).not.toContain('active');
        expect(items[1].classes()).not.toContain('unresolved');
        expect(items[2].classes()).not.toContain('unresolved');
    });

    it('tags internal threads only', () => {
        const wrapper = mountSidebar({
            threads: [
                thread({ id: 't-1', isInternal: true }),
                thread({ id: 't-2' }),
            ],
        });

        const items = wrapper.findAll('.thread-list .sidebar-item');
        expect(items[0].find('.thread-internal').text()).toContain('Internal');
        expect(items[1].find('.thread-internal').exists()).toBe(false);
    });

    it('badges resolved threads for staff only', () => {
        const threads = [
            thread({ id: 't-1', isResolved: true }),
            thread({ id: 't-2' }),
        ];
        const applicant = mountSidebar({ threads });
        expect(applicant.find('.thread-resolved').exists()).toBe(false);

        useUserStore().state.profile = { is_superuser: true } as UserResponse;
        const items = mountSidebar({ threads }).findAll(
            '.thread-list .sidebar-item',
        );
        expect(items[0].find('.thread-resolved').text()).toContain('Resolved');
        expect(items[1].find('.thread-resolved').exists()).toBe(false);
    });

    // Every thread an applicant sees is external, so only staff get the badge.
    it('badges external threads for staff only', () => {
        const threads = [
            thread({ id: 't-1' }),
            thread({ id: 't-2', isInternal: true }),
        ];
        const applicant = mountSidebar({ threads });
        expect(applicant.find('.thread-external').exists()).toBe(false);

        useUserStore().state.profile = { is_superuser: true } as UserResponse;
        const items = mountSidebar({ threads }).findAll(
            '.thread-list .sidebar-item',
        );
        expect(items[0].find('.thread-external').text()).toContain('External');
        expect(items[1].find('.thread-external').exists()).toBe(false);
        expect(items[1].find('.thread-internal').exists()).toBe(true);
    });

    it('emits the thread the user picked', async () => {
        const wrapper = mountSidebar();

        await wrapper.find('.thread-list .sidebar-item').trigger('click');

        expect(wrapper.emitted('select-thread')).toEqual([['t-1']]);
    });

    it('names the empty state after the tab', () => {
        expect(mountSidebar({ threads: [] }).find('.empty-note').text()).toBe(
            'No messages.',
        );
        expect(
            mountSidebar({ threads: [], showArchived: true })
                .find('.empty-note')
                .text(),
        ).toBe('No archived messages.');
    });

    it('always offers the new-message entry and emits it', async () => {
        const wrapper = mountSidebar({ selectedThreadId: NEW_THREAD_ID });
        const entry = wrapper.find('.new-message-item');

        expect(entry.classes()).toContain('active');
        await entry.trigger('click');

        expect(wrapper.emitted('select-thread')).toEqual([[NEW_THREAD_ID]]);
    });
});

describe('MessageAttachmentsField', () => {
    // File.size is read-only, so the content sets it.
    const file = (name: string, size = 1024) =>
        new File([new Uint8Array(size)], name, { type: 'text/plain' });

    const mountField = (files: File[] = []) =>
        mount(MessageAttachmentsField, {
            props: { files, resetKey: 'key-1' },
        });

    it('stages nothing until the widget reports a file', () => {
        expect(mountField().find('.staged-attachments').exists()).toBe(false);
    });

    it('lifts the raw files out of the widget payload', () => {
        const wrapper = mountField();
        const plan = file('plan.pdf');

        wrapper
            .findComponent({ name: 'GenericWidget' })
            .vm.$emit('update:aliasedNodeData', {
                display_value: 'plan.pdf',
                node_value: [{ file: plan }, { file: undefined }],
                details: [],
            });

        // Entries without a file (a widget row still uploading) are dropped.
        expect(wrapper.emitted('update:files')).toEqual([[[plan]]]);
    });

    it('lists each staged file with its size and drops the one removed', async () => {
        const first = file('a.pdf', 2048);
        const second = file('b.pdf');
        const wrapper = mountField([first, second]);

        expect(wrapper.find('.staged-name').text()).toBe('a.pdf');
        expect(wrapper.find('.staged-size').text()).toBe('2 KB');

        await wrapper.findAll('.staged-remove')[0].trigger('click');

        expect(wrapper.emitted('update:files')).toEqual([[[second]]]);
    });
});
