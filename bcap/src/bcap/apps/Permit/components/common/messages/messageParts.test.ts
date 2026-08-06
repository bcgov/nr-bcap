import { mount } from '@vue/test-utils';
import type { FormattedMessage, MessageThread } from '@/bcap/types.ts';

const { downloadFile } = vi.hoisted(() => ({ downloadFile: vi.fn() }));
vi.mock('@/bcap/util.ts', async (importOriginal) => ({
    ...(await importOriginal<typeof import('@/bcap/util.ts')>()),
    downloadFile,
}));

// The real file widget's package cannot be transformed under vitest.
vi.mock(
    '@/arches_component_lab/generics/GenericWidget/GenericWidget.vue',
    () => ({
        default: {
            name: 'GenericWidget',
            emits: ['update:value'],
            template: '<div class="mock-widget" />',
        },
    }),
);

import MessageHistory from './MessageHistory.vue';
import MessageThreadSidebar from './MessageThreadSidebar.vue';
import MessageAttachmentsField from './MessageAttachmentsField.vue';

const message = (overrides: Partial<FormattedMessage> = {}) =>
    ({
        author: 'Hopper, Grace',
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
        hasUnread: false,
        isResolved: false,
        ...overrides,
    }) as MessageThread;

beforeEach(() => {
    downloadFile.mockReset();
});

describe('MessageHistory', () => {
    it('shows only the loading note while messages are in flight', () => {
        const wrapper = mount(MessageHistory, {
            props: { messages: [message()], isLoading: true },
        });

        expect(wrapper.find('.messages-loading').exists()).toBe(true);
        expect(wrapper.find('.historical-message').exists()).toBe(false);
    });

    it('renders each message with its author and text', () => {
        const wrapper = mount(MessageHistory, {
            props: {
                messages: [
                    message(),
                    message({ author: 'Turing, Alan', text: 'Attached.' }),
                ],
                isLoading: false,
            },
        });

        expect(wrapper.findAll('.historical-message')).toHaveLength(2);
        expect(wrapper.text()).toContain('Hopper, Grace');
        expect(wrapper.text()).toContain('Please attach the site plan.');
    });

    it('lists attachments with a human-readable size', () => {
        const wrapper = mount(MessageHistory, {
            props: {
                messages: [
                    message({
                        attachments: [
                            { url: '/f/1', name: 'plan.pdf', size: 2048 },
                        ],
                    }),
                ],
                isLoading: false,
            },
        });

        expect(wrapper.find('.attachment-name').text()).toBe('plan.pdf');
        expect(wrapper.find('.attachment-size').text()).toBe('2 KB');
    });

    it('downloads through the helper rather than following the link', async () => {
        const wrapper = mount(MessageHistory, {
            props: {
                messages: [
                    message({
                        attachments: [
                            { url: '/f/1', name: 'plan.pdf', size: 10 },
                        ],
                    }),
                ],
                isLoading: false,
            },
        });

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

    it('flags the selected, unread and resolved threads', () => {
        const wrapper = mountSidebar({
            threads: [
                thread({ id: 't-1', hasUnread: true }),
                thread({ id: 't-2', isResolved: true }),
            ],
            selectedThreadId: 't-1',
        });

        const items = wrapper.findAll('.thread-list .sidebar-item');
        expect(items[0].classes()).toContain('active');
        expect(items[0].classes()).toContain('unread');
        expect(items[1].classes()).not.toContain('active');
        expect(items[1].classes()).toContain('resolved');
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
        const wrapper = mountSidebar({ selectedThreadId: 'new' });
        const entry = wrapper.find('.new-message-item');

        expect(entry.classes()).toContain('active');
        await entry.trigger('click');

        expect(wrapper.emitted('select-thread')).toEqual([['new']]);
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
            .vm.$emit('update:value', [{ file: plan }, { file: undefined }]);

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
