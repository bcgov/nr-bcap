import { mount, flushPromises } from '@vue/test-utils';
import MessageDialog from './MessageDialog.vue';
import {
    createBcapMessage,
    markMessageAsRead,
    getContributorsForResources,
    getThreadsForResource,
    getMessagesForThread,
} from '@/bcap/apps/Permit/api.ts';
import type { MessageThread } from '@/bcap/types.ts';

vi.mock('@/bcap/apps/Permit/api.ts', () => ({
    createBcapMessage: vi.fn(),
    markMessageAsRead: vi.fn(),
    getContributorsForResources: vi.fn(),
    getThreadsForResource: vi.fn(),
    getMessagesForThread: vi.fn(),
    setThreadArchived: vi.fn(),
}));

describe('MessageDialog.vue', () => {
    beforeEach(() => {
        vi.clearAllMocks();

        vi.mocked(getContributorsForResources).mockResolvedValue([
            { label: 'John Doe', value: 'user-1' },
            { label: 'Jane Smith', value: 'user-2' },
        ]);
        vi.mocked(getThreadsForResource).mockResolvedValue([]);
        vi.mocked(getMessagesForThread).mockResolvedValue([]);
    });

    // node_value carries reference objects, not labels, so a topic that reads
    // back as the label proves the dialog took it from display_value.
    const topicNode = (label: string) => ({
        display_value: label,
        node_value: [
            { list_id: 'list-1', uri: 'https://example.org/1', labels: [] },
        ],
        details: [],
    });

    // The dialog loads its own threads; the archived tab loads a second list.
    const withThreads = (active: unknown[], archived: unknown[] = []) => {
        vi.mocked(getThreadsForResource).mockImplementation(
            (_resourceId: string, isArchived?: boolean) =>
                Promise.resolve(
                    (isArchived ? archived : active) as MessageThread[],
                ),
        );
    };

    // Stub the PrimeVue components to avoid Teleport/DOM issues in tests.
    const mountComponent = (props = {}) => {
        return mount(MessageDialog, {
            props: {
                applicationId: 'APP-1234',
                resourceId: 'permit-999',
                ...props,
            },
            global: {
                stubs: {
                    Dialog: {
                        template:
                            '<div v-if="visible" class="mock-dialog"><slot name="header"></slot><slot></slot><slot name="footer"></slot></div>',
                        props: ['visible'],
                    },
                    Button: {
                        template:
                            '<button class="mock-button" @click="$emit(\'click\')"><slot>{{ label }}</slot></button>',
                        props: ['label', 'loading'],
                    },
                    Textarea: {
                        template:
                            '<textarea :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)"></textarea>',
                        props: ['modelValue'],
                    },
                    Dropdown: {
                        template:
                            '<select :value="modelValue" @change="$emit(\'update:modelValue\', $event.target.value)"></select>',
                        props: ['modelValue', 'options', 'loading'],
                    },
                },
            },
        });
    };

    it('loads contributors when opened, not on mount, and selects the first one', async () => {
        const wrapper = mountComponent();
        await flushPromises();

        expect(getContributorsForResources).not.toHaveBeenCalled();

        await wrapper.findAll('.mock-button')[0].trigger('click');
        await flushPromises();

        expect(getContributorsForResources).toHaveBeenCalledWith('permit-999');

        expect((wrapper.vm as unknown).state.recipients.length).toBe(2);
        expect((wrapper.vm as unknown).state.selectedRecipient).toBe('user-1');
    });

    it('renders the "View Messages" trigger without a badge when there are no unread threads', async () => {
        const wrapper = mountComponent();
        await flushPromises();

        expect(getThreadsForResource).toHaveBeenCalledWith('permit-999', false);

        const triggerBtn = wrapper.findAll('.mock-button')[0];
        expect(triggerBtn.text()).toContain('Messages');
        expect(wrapper.find('.message-badge').exists()).toBe(false);
    });

    it('renders the badge when threads have unread messages', async () => {
        withThreads([
            {
                id: 't1',
                topic: 'General Question',
                messages: [],
                hasUnread: true,
                unreadCount: 3,
            },
        ]);

        const wrapper = mountComponent();
        await flushPromises();

        const triggerBtn = wrapper.findAll('.mock-button')[0];
        expect(triggerBtn.text()).toContain('Messages');

        const badge = wrapper.find('.message-badge');
        expect(badge.exists()).toBe(true);
        expect(badge.text()).toBe('3');
    });

    it('loads threads on mount so unread counts are ready before the dialog opens', async () => {
        withThreads([
            {
                id: 't1',
                topic: 'General Question',
                messages: [],
                hasUnread: true,
                unreadCount: 4,
            },
        ]);

        const wrapper = mountComponent();
        await flushPromises();

        // No dialog open yet: the fetch and the badge both come from mount.
        expect(wrapper.find('.mock-dialog').exists()).toBe(false);
        expect(getThreadsForResource).toHaveBeenCalledWith('permit-999', false);
        expect(wrapper.find('.message-badge').text()).toBe('4');
    });

    // The dialog is scoped to its resource id, so it lists every thread on that
    // resource and the badge sums their unread counts.
    it('lists every thread on the resource and sums their unread counts', async () => {
        withThreads([
            {
                id: 't1',
                topic: 'Site Plan general question',
                messages: [],
                hasUnread: true,
                unreadCount: 2,
            },
            {
                id: 't2',
                topic: 'Water Licence general question',
                messages: [],
                hasUnread: true,
                unreadCount: 5,
            },
        ]);

        const wrapper = mountComponent();
        await flushPromises();

        await wrapper.findAll('.mock-button')[0].trigger('click');
        await flushPromises();

        expect(wrapper.find('.message-badge').text()).toBe('7');

        const topics = wrapper.findAll('.thread-topic-label');
        expect(topics.map((t) => t.text())).toEqual([
            'Site Plan general question',
            'Water Licence general question',
        ]);
    });

    it('opens the dialog when the trigger button is clicked', async () => {
        const wrapper = mountComponent();
        await flushPromises();

        expect(wrapper.find('.mock-dialog').exists()).toBe(false);

        await wrapper.findAll('.mock-button')[0].trigger('click');
        await flushPromises();

        expect(wrapper.find('.mock-dialog').exists()).toBe(true);
        expect(wrapper.html()).toContain('Permit Application');
    });

    it('displays existing messages in the thread when a sidebar thread is selected (Reply mode)', async () => {
        withThreads([
            {
                id: 'thread-555',
                topic: 'General Question',
                hasUnread: false,
            },
        ]);
        // Messages are fetched for the open thread, not carried on the list.
        vi.mocked(getMessagesForThread).mockResolvedValue([
            {
                id: 'msg-1',
                author: 'Jane',
                text: 'Please fix this',
                date: 'Oct 1',
                isUnread: false,
                attachments: [],
            },
        ]);

        const wrapper = mountComponent();
        await flushPromises();

        await wrapper.findAll('.mock-button')[0].trigger('click');
        await flushPromises();

        await wrapper.findAll('.sidebar-item')[0].trigger('click');
        await flushPromises();

        const thread = wrapper.find('.message-thread');
        expect(thread.exists()).toBe(true);
        expect(thread.html()).toContain('Jane');
        expect(thread.html()).toContain('Please fix this');
        expect(thread.html()).toContain('Oct 1');
    });

    it('does not call submit if message text is empty', async () => {
        const wrapper = mountComponent();
        await flushPromises();

        await wrapper.findAll('.mock-button')[0].trigger('click');
        await flushPromises();

        // Index 1 is the Send button in the new-message view.
        await wrapper.findAll('.mock-button')[1].trigger('click');

        expect(createBcapMessage).not.toHaveBeenCalled();
    });

    it('submits a NEW message successfully and reloads the thread list', async () => {
        vi.mocked(createBcapMessage).mockResolvedValue({
            id: 'msg-123',
            success: true,
        });

        const wrapper = mountComponent();
        await flushPromises();

        await wrapper.findAll('.mock-button')[0].trigger('click');
        await flushPromises();

        await wrapper
            .findComponent({ name: 'GenericWidget' })
            .vm.$emit('update:aliasedNodeData', topicNode('General Question'));
        await wrapper.find('.subject-input').setValue('Setback dimensions');
        await wrapper.find('textarea').setValue('This is my question.');

        await wrapper.findAll('.mock-button')[1].trigger('click');
        await flushPromises();

        expect(createBcapMessage).toHaveBeenCalledWith({
            messageText: 'This is my question.',
            recipientId: 'user-1',
            resourceId: 'permit-999',
            threadId: undefined,
            topic: 'Setback dimensions',
            messageType: [
                { list_id: 'list-1', uri: 'https://example.org/1', labels: [] },
            ],
            files: [],
        });

        // The store fetches this resource's threads on mount, again when the
        // dialog opens, and once more after the send.
        expect(vi.mocked(getThreadsForResource).mock.calls).toEqual([
            ['permit-999', false],
            ['permit-999', false],
            ['permit-999', false],
        ]);

        expect(wrapper.find('.mock-dialog').exists()).toBe(false);
    });

    it('marks unread messages as read when an unread thread is selected', async () => {
        withThreads([
            {
                id: 'thread-999',
                topic: 'Modification Request',
                hasUnread: true,
                unreadCount: 1,
            },
        ]);
        vi.mocked(getMessagesForThread).mockResolvedValue([
            {
                id: 'msg-55',
                author: 'Ministry',
                text: 'Needs update',
                date: '',
                isUnread: true,
                attachments: [],
            },
        ]);

        const wrapper = mountComponent();
        await flushPromises();

        await wrapper.findAll('.mock-button')[0].trigger('click');
        await flushPromises();

        await wrapper.findAll('.sidebar-item')[0].trigger('click');
        await flushPromises();

        expect(markMessageAsRead).toHaveBeenCalledWith('msg-55');
        expect(markMessageAsRead).toHaveBeenCalledTimes(1);
    });

    // The typed subject and the picked type travel as separate nodes; the
    // thread list composes them for display. context never filters the view.
    it('sends the subject and the picked type separately', async () => {
        vi.mocked(createBcapMessage).mockResolvedValue({ id: 'msg-123' });

        const wrapper = mountComponent({ context: 'Investigation' });
        await flushPromises();

        await wrapper.findAll('.mock-button')[0].trigger('click');
        await flushPromises();

        expect(wrapper.html()).toContain('Investigation');

        await wrapper
            .findComponent({ name: 'GenericWidget' })
            .vm.$emit('update:aliasedNodeData', topicNode('General Question'));
        await wrapper.find('.subject-input').setValue('Trench depth');
        await wrapper.find('textarea').setValue('A question.');
        await wrapper.findAll('.mock-button')[1].trigger('click');
        await flushPromises();

        expect(createBcapMessage).toHaveBeenCalledWith({
            messageText: 'A question.',
            recipientId: 'user-1',
            resourceId: 'permit-999',
            threadId: undefined,
            topic: 'Trench depth',
            messageType: [
                { list_id: 'list-1', uri: 'https://example.org/1', labels: [] },
            ],
            files: [],
        });
    });

    // A new thread needs a message type, so Send stays disabled until one is
    // picked; typing text alone posts nothing.
    it('does not send a new thread without a message type', async () => {
        const wrapper = mountComponent();
        await flushPromises();

        await wrapper.findAll('.mock-button')[0].trigger('click');
        await flushPromises();

        await wrapper.find('textarea').setValue('No topic picked.');
        await wrapper.findAll('.mock-button')[1].trigger('click');
        await flushPromises();

        expect(createBcapMessage).not.toHaveBeenCalled();
    });

    // The attachments widget emits an entry per file with the raw File in .file;
    // the dialog forwards those Files to the create call.
    it('sends attached files with a new message', async () => {
        vi.mocked(createBcapMessage).mockResolvedValue({ id: 'msg-file' });

        const wrapper = mountComponent();
        await flushPromises();

        await wrapper.findAll('.mock-button')[0].trigger('click');
        await flushPromises();

        // Topic widget first, attachments widget second.
        const widgets = wrapper.findAllComponents({ name: 'GenericWidget' });
        await widgets[0].vm.$emit(
            'update:aliasedNodeData',
            topicNode('General Question'),
        );
        const file = new File(['x'], 'plan.pdf');
        await widgets[1].vm.$emit('update:aliasedNodeData', {
            display_value: 'plan.pdf',
            node_value: [{ name: 'plan.pdf', file }],
            details: [],
        });
        await wrapper.find('.subject-input').setValue('Site plan');
        await wrapper.find('textarea').setValue('See attached.');
        await wrapper.findAll('.mock-button')[1].trigger('click');
        await flushPromises();

        expect(createBcapMessage).toHaveBeenCalledWith(
            expect.objectContaining({
                messageText: 'See attached.',
                topic: 'Site plan',
                files: [file],
            }),
        );
    });

    it('submits a REPLY to an existing thread successfully', async () => {
        vi.mocked(createBcapMessage).mockResolvedValue({
            id: 'msg-reply',
            success: true,
        });

        withThreads([
            {
                id: 'thread-777',
                topic: 'Investigation question',
                hasUnread: false,
                messages: [
                    {
                        id: 'm1',
                        author: 'Ministry',
                        text: 'Hi',
                        isUnread: false,
                    },
                ],
            },
        ]);

        const wrapper = mountComponent();
        await flushPromises();

        await wrapper.findAll('.mock-button')[0].trigger('click');
        await flushPromises();

        await wrapper.findAll('.sidebar-item')[0].trigger('click');
        await flushPromises();

        await wrapper.find('textarea').setValue('This is my reply.');

        const sendReplyBtn = wrapper
            .findAll('.mock-button')
            .find((b) => b.text().includes('Send'));
        await sendReplyBtn?.trigger('click');
        await flushPromises();

        // A reply carries its thread id and inherits the thread's topic.
        expect(createBcapMessage).toHaveBeenCalledWith({
            messageText: 'This is my reply.',
            recipientId: 'user-1',
            resourceId: 'permit-999',
            threadId: 'thread-777',
            topic: undefined,
            files: [],
        });
    });
});
