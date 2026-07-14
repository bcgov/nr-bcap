import { mount, flushPromises } from '@vue/test-utils';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import QuestionDialogExternal from './QuestionDialogExternal.vue';
import { createBcapMessage, getContributors } from '@/bcap/apps/Permit/api.ts';

// 1. Mock the API calls
vi.mock('@/bcap/apps/Permit/api.ts', () => ({
    createBcapMessage: vi.fn(),
    getContributors: vi.fn(),
}));

describe('QuestionDialogExternal.vue', () => {
    beforeEach(() => {
        vi.clearAllMocks();

        // Default successful response for getContributors
        vi.mocked(getContributors).mockResolvedValue([
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

        expect(getContributors).toHaveBeenCalledOnce();

        // Verify internal state (selectedRecipient should default to the first value)
        expect(wrapper.vm.recipients.length).toBe(2);
        expect(wrapper.vm.selectedRecipient).toBe('user-1');
    });

    it('renders the "Ask a question" trigger when in New Question mode', async () => {
        const wrapper = mountComponent();
        await flushPromises();

        const triggerBtn = wrapper.findAll('.mock-button')[0];
        expect(triggerBtn.text()).toContain('Ask a question');

        // Badge should not exist
        const badge = wrapper.find('.message-badge');
        expect(badge.exists()).toBe(false);
    });

    it('renders the "View message" trigger and badge when in Reply mode', async () => {
        const wrapper = mountComponent({
            existingMessages: [{ author: 'System', text: 'Needs more info' }],
        });
        await flushPromises();

        const triggerBtn = wrapper.findAll('.mock-button')[0];
        expect(triggerBtn.text()).toContain('View message');

        // Badge should exist
        const badge = wrapper.find('.message-badge');
        expect(badge.exists()).toBe(true);
        expect(badge.text()).toBe('!');
    });

    it('opens the dialog when the trigger button is clicked', async () => {
        const wrapper = mountComponent();
        await flushPromises();

        // Dialog should be hidden initially
        expect(wrapper.find('.mock-dialog').exists()).toBe(false);

        // Click trigger
        await wrapper.findAll('.mock-button')[0].trigger('click');
        await flushPromises();

        // Dialog should now be visible
        expect(wrapper.find('.mock-dialog').exists()).toBe(true);
        expect(wrapper.html()).toContain('Comment on Application APP-1234');
    });

    it('displays existing messages in the thread when in Reply mode', async () => {
        const wrapper = mountComponent({
            existingMessages: [
                { author: 'Jane', text: 'Please fix this', date: 'Oct 1' },
            ],
        });
        await flushPromises();

        // Open dialog
        await wrapper.findAll('.mock-button')[0].trigger('click');
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

        // Click Send without typing anything (second button is the submit footer button)
        await wrapper.findAll('.mock-button')[1].trigger('click');

        expect(createBcapMessage).not.toHaveBeenCalled();
    });

    it('submits a new message successfully and emits event', async () => {
        const mockResponseData = { id: 'msg-123', success: true };
        vi.mocked(createBcapMessage).mockResolvedValue(mockResponseData);

        const wrapper = mountComponent({
            threadId: 'thread-555',
        });
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

        // Verify API call
        expect(createBcapMessage).toHaveBeenCalledWith(
            'This is my question.',
            'user-1', // Default selected recipient
            'APP-1234',
            'permit-999',
            'thread-555',
        );

        // Verify it emitted the success event with API response
        expect(wrapper.emitted('message-sent')).toBeTruthy();
        expect(wrapper.emitted('message-sent')?.[0]).toEqual([
            mockResponseData,
        ]);

        // Verify dialog closes
        expect(wrapper.find('.mock-dialog').exists()).toBe(false);
    });
});
