import { mount, flushPromises } from '@vue/test-utils';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import QuestionDialogExternal from './QuestionDialogExternal.vue';
import {
    createBcapMessage,
    getContributors,
    markMessageAsRead,
} from '@/bcap/apps/Permit/api.ts';

// 1. Mock the API calls
vi.mock('@/bcap/apps/Permit/api.ts', () => ({
    createBcapMessage: vi.fn(),
    getContributors: vi.fn(),
    markMessageAsRead: vi.fn(),
}));

describe('QuestionDialogExternal.vue', () => {
    beforeEach(() => {
        vi.clearAllMocks();

        // Default successful response for the recipient fetch
        vi.mocked(getContributorsForResources).mockResolvedValue([
            { label: 'John Doe', value: 'user-1' },
            { label: 'Jane Smith', value: 'user-2' },
        ]);
    });

    const mountComponent = (props = {}) => {
        return mount(QuestionDialogExternal, {
            props: {
                applicationId: 'APP-1234',
                permitResourceId: 'permit-999',
                ...props,
            },
            global: {
                // Stub PrimeVue components to avoid Teleport/DOM issues in tests
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

    it('loads contributors on mount and selects the first one', async () => {
        const wrapper = mountComponent();
        await flushPromises();

        expect(getContributorsForResources).toHaveBeenCalledOnce();
        expect(getContributorsForResources).toHaveBeenCalledWith('permit-999');

        // Use 'as any' to bypass the <script setup> private instance TypeScript error
        expect((wrapper.vm as unknown).recipients.length).toBe(2);
        expect((wrapper.vm as unknown).selectedRecipient).toBe('user-1');
    });

    it('renders the "View Messages" trigger without a badge when there are no unread threads', async () => {
        const wrapper = mountComponent({ threads: [] });
        await flushPromises();

        const triggerBtn = wrapper.findAll('.mock-button')[0];
        expect(triggerBtn.text()).toContain('View Messages');

        // Badge should not exist
        const badge = wrapper.find('.message-badge');
        expect(badge.exists()).toBe(false);
    });

    it('renders the badge when threads have unread messages', async () => {
        const wrapper = mountComponent({
            threads: [
                {
                    id: 't1',
                    topic: 'General Question',
                    messages: [],
                    hasUnread: true,
                    unreadCount: 3,
                },
            ],
        });
        await flushPromises();

        const triggerBtn = wrapper.findAll('.mock-button')[0];
        expect(triggerBtn.text()).toContain('View Messages');

        // Badge should exist and sum the unread count
        const badge = wrapper.find('.message-badge');
        expect(badge.exists()).toBe(true);
        expect(badge.text()).toBe('3');
    });

    it('opens the dialog when the trigger button is clicked', async () => {
        const wrapper = mountComponent();
        await flushPromises();

        // Dialog should be hidden initially
        expect(wrapper.find('.mock-dialog').exists()).toBe(false);

        // Click trigger
        await wrapper.findAll('.mock-button')[0].trigger('click');
        await flushPromises();

        // Dialog should now be visible with the new title
        expect(wrapper.find('.mock-dialog').exists()).toBe(true);
        expect(wrapper.html()).toContain('Comments on Application APP-1234');
    });

    it('displays existing messages in the thread when a sidebar thread is selected (Reply mode)', async () => {
        const wrapper = mountComponent({
            threads: [
                {
                    id: 'thread-555',
                    topic: 'General Question',
                    hasUnread: false,
                    messages: [
                        {
                            id: 'msg-1',
                            author: 'Jane',
                            text: 'Please fix this',
                            date: 'Oct 1',
                            isUnread: false,
                        },
                    ],
                },
            ],
        });
        await flushPromises();

        // Open dialog
        await wrapper.findAll('.mock-button')[0].trigger('click');
        await flushPromises();

        // Click the first sidebar item to select the thread
        const sidebarItems = wrapper.findAll('.sidebar-item');
        await sidebarItems[0].trigger('click');
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

        // Open dialog
        await wrapper.findAll('.mock-button')[0].trigger('click');
        await flushPromises();

        // Click Send without typing anything (index 1 is the Send button in new message view)
        await wrapper.findAll('.mock-button')[1].trigger('click');

        expect(createBcapMessage).not.toHaveBeenCalled();
    });

    it('submits a NEW message successfully and emits event', async () => {
        const mockResponseData = { id: 'msg-123', success: true };
        vi.mocked(createBcapMessage).mockResolvedValue(mockResponseData);

        const wrapper = mountComponent();
        await flushPromises();

        // Open dialog
        await wrapper.findAll('.mock-button')[0].trigger('click');
        await flushPromises();

        // Type a message
        const textarea = wrapper.find('textarea');
        await textarea.setValue('This is my question.');

        // Click Send
        await wrapper.findAll('.mock-button')[1].trigger('click');
        await flushPromises();

        // Verify API call for a new thread (undefined thread ID, default 'General Question' topic)
        expect(createBcapMessage).toHaveBeenCalledWith(
            'This is my question.',
            'user-1', // Default selected recipient
            'APP-1234',
            'permit-999',
            undefined,
            'General general question',
        );

        // Verify it emitted the success event with API response
        expect(wrapper.emitted('message-sent')).toBeTruthy();
        expect(wrapper.emitted('message-sent')?.[0]).toEqual([
            mockResponseData,
        ]);

        // Verify dialog closes
        expect(wrapper.find('.mock-dialog').exists()).toBe(false);
    });

    it('marks unread messages as read when an unread thread is selected', async () => {
        const wrapper = mountComponent({
            threads: [
                {
                    id: 'thread-999',
                    topic: 'Modification Request',
                    hasUnread: true,
                    unreadCount: 1,
                    messages: [
                        {
                            id: 'msg-55',
                            author: 'Ministry',
                            text: 'Needs update',
                            isUnread: true,
                        },
                    ],
                },
            ],
        });
        await flushPromises();

        // Open dialog
        await wrapper.findAll('.mock-button')[0].trigger('click');
        await flushPromises();

        // Click the sidebar item to select the unread thread
        const sidebarItems = wrapper.findAll('.sidebar-item');
        // Index 0 is the thread we just passed in props
        await sidebarItems[0].trigger('click');
        await flushPromises();

        // Verify the API was called to mark the specific message as read
        expect(markMessageAsRead).toHaveBeenCalledWith('msg-55');
        expect(markMessageAsRead).toHaveBeenCalledTimes(1);
    });

    // -------------------------------------------------------------------------
    // NEW TESTS
    // -------------------------------------------------------------------------

    it('combines custom context and topic when context prop is provided', async () => {
        vi.mocked(createBcapMessage).mockResolvedValue({
            id: 'msg-123',
            success: true,
        });

        // Pass a custom context instead of relying on the default 'General'
        const wrapper = mountComponent({ context: 'Alteration Module' });
        await flushPromises();

        // Open dialog
        await wrapper.findAll('.mock-button')[0].trigger('click');
        await flushPromises();

        // Type a message
        await wrapper
            .find('textarea')
            .setValue('This is an alteration question.');

        // Click Send
        await wrapper.findAll('.mock-button')[1].trigger('click');
        await flushPromises();

        // Verify the topic sent to the API is specifically mapped to the custom context
        expect(createBcapMessage).toHaveBeenCalledWith(
            'This is an alteration question.',
            'user-1',
            'APP-1234',
            'permit-999',
            undefined,
            'Alteration Module general question', // Custom context + default dropdown topic
        );
    });

    it('submits a REPLY to an existing thread successfully', async () => {
        vi.mocked(createBcapMessage).mockResolvedValue({
            id: 'msg-reply',
            success: true,
        });

        const wrapper = mountComponent({
            threads: [
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
            ],
        });
        await flushPromises();

        // Open dialog
        await wrapper.findAll('.mock-button')[0].trigger('click');
        await flushPromises();

        // Select the thread to enter reply mode
        await wrapper.findAll('.sidebar-item')[0].trigger('click');
        await flushPromises();

        // Type a reply
        await wrapper.find('textarea').setValue('This is my reply.');

        // Find the Send button in the reply area.
        // We look through all mock buttons and find the one that submits the reply.
        // It's likely the last or second to last button in the DOM at this point.
        const allButtons = wrapper.findAll('.mock-button');
        const sendReplyBtn = allButtons.find((b) => b.text().includes('Send'));

        await sendReplyBtn?.trigger('click');
        await flushPromises();

        // Verify API call for a reply (includes thread ID, omits formatted topic)
        expect(createBcapMessage).toHaveBeenCalledWith(
            'This is my reply.',
            'user-1', // Default selected recipient
            'APP-1234',
            'permit-999',
            'thread-777', // Target Thread ID is included!
            undefined, // Topic should be undefined for replies
        );
    });
});
