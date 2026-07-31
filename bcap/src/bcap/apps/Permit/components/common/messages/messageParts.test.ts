import { describe, it, expect, vi, beforeEach } from 'vitest';
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

    it('leaves the date out when the message has none', () => {
        const wrapper = mount(MessageHistory, {
            props: { messages: [message({ date: '' })], isLoading: false },
        });

        expect(wrapper.find('.message-date').exists()).toBe(false);
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

    it('omits the size for an attachment that has none', () => {
        const wrapper = mount(MessageHistory, {
            props: {
                messages: [
                    message({
                        attachments: [{ url: '/f/1', name: 'plan.pdf' }],
                    }),
                ],
                isLoading: false,
            },
        });

        expect(wrapper.find('.attachment-size').exists()).toBe(false);
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

    it('marks the tab matching the archived flag', () => {
        const active = mountSidebar().findAll('.sidebar-tab');
        expect(active[0].classes()).toContain('active');
        expect(active[1].classes()).not.toContain('active');

        const archived = mountSidebar({ showArchived: true }).findAll(
            '.sidebar-tab',
        );
        expect(archived[1].classes()).toContain('active');
    });

    it('emits the tab the user picked', async () => {
        const wrapper = mountSidebar();

        await wrapper.findAll('.sidebar-tab')[1].trigger('click');

        expect(wrapper.emitted('select-tab')).toEqual([[true]]);
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

    it('leaves the date out for a thread with no messages yet', () => {
        const wrapper = mountSidebar({
            threads: [thread({ lastMessageDate: '' })],
        });

        expect(wrapper.find('.thread-date').exists()).toBe(false);
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

    it('lifts the raw files out of the widget payload', async () => {
        const wrapper = mountField();
        const plan = file('plan.pdf');

        wrapper
            .findComponent({ name: 'GenericWidget' })
            .vm.$emit('update:value', [{ file: plan }, { file: undefined }]);

        // Entries without a file (a widget row still uploading) are dropped.
        expect(wrapper.emitted('update:files')).toEqual([[[plan]]]);
    });

    it('treats an empty widget payload as no files', () => {
        const wrapper = mountField();

        wrapper
            .findComponent({ name: 'GenericWidget' })
            .vm.$emit('update:value', undefined);

        expect(wrapper.emitted('update:files')).toEqual([[[]]]);
    });

    it('lists each staged file with its size', () => {
        const wrapper = mountField([file('plan.pdf', 2048)]);

        expect(wrapper.find('.staged-name').text()).toBe('plan.pdf');
        expect(wrapper.find('.staged-size').text()).toBe('2 KB');
    });

    it('emits the remaining files when one is removed', async () => {
        const first = file('a.pdf');
        const second = file('b.pdf');
        const wrapper = mountField([first, second]);

        await wrapper.findAll('.staged-remove')[0].trigger('click');

        expect(wrapper.emitted('update:files')).toEqual([[[second]]]);
    });
});
