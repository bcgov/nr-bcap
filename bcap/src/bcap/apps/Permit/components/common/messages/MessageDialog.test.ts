import { mount, flushPromises } from '@vue/test-utils';
import MessageDialog from './MessageDialog.vue';
import {
    createBcapMessage,
    getContributorsForResources,
    getThreadsForResource,
    getMessagesForThread,
    setThreadArchived,
    setThreadResolved,
} from '@/bcap/apps/Permit/api.ts';
import { ApiError } from '@/bcap/api.ts';
import type { MessageThread } from '@/bcap/types.ts';
import { useUserStore } from '@/bcap/stores/user.ts';
import type { UserResponse } from '@/bcap/client/types.gen.ts';

vi.mock('@/bcap/apps/Permit/api.ts', () => ({
    createBcapMessage: vi.fn(),
    getContributorsForResources: vi.fn(),
    getThreadsForResource: vi.fn(),
    getMessagesForThread: vi.fn(),
    setThreadArchived: vi.fn(),
    setThreadResolved: vi.fn(),
}));

const thread = (over: Partial<MessageThread> = {}): MessageThread => ({
    id: 't1',
    topic: 'General Question',
    startedBy: 'Amy',
    lastMessageDate: '',
    isResolved: false,
    onSide: true,
    resolvedBy: '',
    resolvedDate: '',
    isInternal: false,
    ...over,
});

describe('MessageDialog.vue', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        // Staff by default; applicant tests clear the profile.
        useUserStore().state.profile = { is_superuser: true } as UserResponse;

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
    const withThreads = (
        active: MessageThread[],
        archived: MessageThread[] = [],
    ) => {
        vi.mocked(getThreadsForResource).mockImplementation(
            (_resourceId: string, isArchived?: boolean) =>
                Promise.resolve(isArchived ? archived : active),
        );
    };

    const button = (wrapper: ReturnType<typeof mount>, label: string) =>
        wrapper.findAll('.mock-button').find((b) => b.text() === label);

    const openThread = async (wrapper: ReturnType<typeof mount>) => {
        await wrapper.findAll('.mock-button')[0].trigger('click');
        await flushPromises();
        await wrapper.findAll('.sidebar-item')[0].trigger('click');
        await flushPromises();
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

    it('renders the "View Messages" trigger without a badge when every thread is resolved', async () => {
        withThreads([thread({ isResolved: true })]);
        const wrapper = mountComponent();
        await flushPromises();

        expect(getThreadsForResource).toHaveBeenCalledWith('permit-999', false);

        const triggerBtn = wrapper.findAll('.mock-button')[0];
        expect(triggerBtn.text()).toContain('Messages');
        expect(wrapper.find('.message-badge').exists()).toBe(false);
    });

    it('loads threads on mount so the unresolved count is ready before the dialog opens', async () => {
        withThreads([
            thread({ id: 't1' }),
            thread({ id: 't2' }),
            thread({ id: 't3', isResolved: true }),
        ]);

        const wrapper = mountComponent();
        await flushPromises();

        // No dialog open yet: the fetch and the badge both come from mount.
        expect(wrapper.find('.mock-dialog').exists()).toBe(false);
        expect(getThreadsForResource).toHaveBeenCalledWith('permit-999', false);
        expect(wrapper.find('.message-badge').text()).toBe('2');
    });

    // The dialog is scoped to its resource id, so it lists every thread on that
    // resource and the badge counts the unresolved ones.
    it('lists every thread on the resource', async () => {
        withThreads([
            thread({ id: 't1', topic: 'Site Plan general question' }),
            thread({ id: 't2', topic: 'Water Licence general question' }),
        ]);

        const wrapper = mountComponent();
        await flushPromises();

        await wrapper.findAll('.mock-button')[0].trigger('click');
        await flushPromises();

        expect(wrapper.find('.message-badge').text()).toBe('2');

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
        withThreads([thread({ id: 'thread-555' })]);
        // Messages are fetched for the open thread, not carried on the list.
        vi.mocked(getMessagesForThread).mockResolvedValue([
            {
                id: 'msg-1',
                author: 'Jane',
                text: 'Please fix this',
                date: 'Oct 1',
                attachments: [],
            },
        ]);

        const wrapper = mountComponent();
        await flushPromises();

        await wrapper.findAll('.mock-button')[0].trigger('click');
        await flushPromises();

        await wrapper.findAll('.sidebar-item')[0].trigger('click');
        await flushPromises();

        const history = wrapper.find('.message-thread');
        expect(history.exists()).toBe(true);
        expect(history.html()).toContain('Jane');
        expect(history.html()).toContain('Please fix this');
        expect(history.html()).toContain('Oct 1');
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

    it('shows the server message and stays open when a send fails', async () => {
        vi.spyOn(console, 'error').mockImplementation(() => {});
        vi.mocked(createBcapMessage).mockRejectedValue(
            new ApiError('These files are not permitted:\nsetup.exe', 400),
        );

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

        const error = wrapper.find('.inline-error');
        expect(error.text()).toContain('Your message could not be sent.');
        expect(error.text()).toContain('setup.exe');
        expect(wrapper.find('.mock-dialog').exists()).toBe(true);
    });

    // The store reports what it loaded, the dialog what it did itself; both go
    // to the one slot at the top.
    it('shows a failed thread load in the slot at the top', async () => {
        vi.spyOn(console, 'error').mockImplementation(() => {});
        vi.mocked(getThreadsForResource).mockRejectedValue(new Error('boom'));

        const wrapper = mountComponent();
        await flushPromises();
        await wrapper.findAll('.mock-button')[0].trigger('click');
        await flushPromises();

        expect(wrapper.find('.dialog-error').text()).toContain(
            'Messages could not be loaded.',
        );
    });

    it('shows a failed recipient load in that same slot', async () => {
        vi.spyOn(console, 'error').mockImplementation(() => {});
        vi.mocked(getContributorsForResources).mockRejectedValue(
            new Error('boom'),
        );

        const wrapper = mountComponent();
        await flushPromises();
        await wrapper.findAll('.mock-button')[0].trigger('click');
        await flushPromises();

        expect(wrapper.findAll('.inline-error')).toHaveLength(1);
        expect(wrapper.find('.dialog-error').text()).toContain(
            'The list of recipients could not be loaded.',
        );
    });

    it('shows who resolved a thread and lets staff reopen it', async () => {
        withThreads([
            thread({
                id: 'thread-1',
                isResolved: true,
                resolvedBy: 'Sam',
                resolvedDate: '2026-02-01T12:00:00Z',
            }),
        ]);
        const reopened = mountComponent();
        await flushPromises();
        await openThread(reopened);

        const tag = reopened.find('.resolved-tag').text();
        expect(tag).toContain('by Sam');
        expect(tag).toContain('2026');
        await button(reopened, 'Mark as Unresolved')?.trigger('click');
        await flushPromises();
        expect(setThreadResolved).toHaveBeenCalledWith('thread-1', false);
    });

    it('only offers Archive once the thread is resolved', async () => {
        withThreads([thread()]);
        const wrapper = mountComponent();
        await flushPromises();
        await openThread(wrapper);

        expect(button(wrapper, 'Archive')).toBeUndefined();
    });

    it('archives a thread for this viewer, and unarchives from the archived tab', async () => {
        withThreads(
            [thread({ id: 'active-1', isResolved: true })],
            [thread({ id: 'arch-1', isResolved: true })],
        );
        const wrapper = mountComponent();
        await flushPromises();
        await openThread(wrapper);

        await button(wrapper, 'Archive')?.trigger('click');
        await flushPromises();
        expect(setThreadArchived).toHaveBeenCalledWith('active-1', true);
        expect(setThreadResolved).not.toHaveBeenCalled();

        await wrapper.findAll('.sidebar-tab')[1].trigger('click');
        await flushPromises();
        await wrapper.findAll('.sidebar-item')[0].trigger('click');
        await flushPromises();
        // An archived thread has to come back before it can be unresolved.
        expect(button(wrapper, 'Mark as Unresolved')).toBeUndefined();
        await button(wrapper, 'Unarchive')?.trigger('click');
        await flushPromises();
        expect(setThreadArchived).toHaveBeenCalledWith('arch-1', false);
    });

    it('marks an internal thread as staff only', async () => {
        withThreads([thread({ isInternal: true })]);
        const wrapper = mountComponent();
        await flushPromises();
        await openThread(wrapper);

        expect(wrapper.find('.internal-tag').text()).toContain('Internal');
        expect(wrapper.find('.external-tag').exists()).toBe(false);
        expect(wrapper.find('.resolved-tag').exists()).toBe(false);
    });

    it('marks a shared thread as external', async () => {
        withThreads([thread()]);
        const wrapper = mountComponent();
        await flushPromises();
        await openThread(wrapper);

        expect(wrapper.find('.external-tag').text()).toContain('External');
        expect(wrapper.find('.internal-tag').exists()).toBe(false);
    });

    it('resolves the applicant side on open, with no resolve controls', async () => {
        useUserStore().state.profile = null;
        withThreads([thread({ id: 'thread-1' })]);
        const wrapper = mountComponent();
        await flushPromises();
        await openThread(wrapper);

        expect(setThreadResolved).toHaveBeenCalledWith('thread-1', true);
        expect(button(wrapper, 'Mark as Resolved')).toBeUndefined();
    });

    it('shows an applicant no thread status tags', async () => {
        useUserStore().state.profile = null;
        withThreads([
            thread({
                isResolved: true,
                resolvedBy: 'Amy',
            }),
        ]);
        const wrapper = mountComponent();
        await flushPromises();
        await openThread(wrapper);

        expect(wrapper.find('.thread-status').exists()).toBe(false);
        expect(setThreadResolved).not.toHaveBeenCalled();
    });

    it('offers no Resolve to a viewer on neither side', async () => {
        withThreads([thread({ onSide: false })]);
        const wrapper = mountComponent();
        await flushPromises();
        await openThread(wrapper);

        expect(button(wrapper, 'Mark as Resolved')).toBeUndefined();
        expect(button(wrapper, 'Archive')).toBeDefined();
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
            thread({ id: 'thread-777', topic: 'Investigation question' }),
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
