import { describe, it, expect, vi, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import MessageDemo from './MessageDemo.vue';

// Basic coverage for the throwaway message-endpoint demo harness. It exercises
// the render and the run/error path; the demo is temporary and will be removed.

afterEach(() => {
    vi.unstubAllGlobals();
});

describe('MessageDemo', () => {
    it('renders the demo panel with a run button', () => {
        const wrapper = mount(MessageDemo);
        expect(wrapper.text()).toContain('BCAP Message endpoint demo');
        expect(wrapper.find('.run-btn').exists()).toBe(true);
    });

    it('runs the demo and surfaces a failure without staying stuck', async () => {
        vi.stubGlobal(
            'fetch',
            vi.fn(() => Promise.reject(new Error('network down'))),
        );
        const wrapper = mount(MessageDemo);

        await wrapper.find('.run-btn').trigger('click');
        await flushPromises();

        expect(wrapper.find('.error').exists()).toBe(true);
        // The run settled, so the button is enabled again.
        expect(
            (wrapper.find('.run-btn').element as HTMLButtonElement).disabled,
        ).toBe(false);
    });
});
