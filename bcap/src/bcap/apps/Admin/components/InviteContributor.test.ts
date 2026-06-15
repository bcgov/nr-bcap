/* eslint-disable vue/one-component-per-file -- test stubs live together */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { defineComponent } from 'vue';
import { mount, flushPromises } from '@vue/test-utils';

// The data source and toast are mocked so the component can be driven in
// isolation without the real API or PrimeVue Toast service.
const getUnlinkedContributors = vi.fn();
const getAssignableGroups = vi.fn();
const issueRegistrationLink = vi.fn();
vi.mock('@/bcap/components/pages/api.ts', () => ({
    getUnlinkedContributors: (...args: unknown[]) =>
        getUnlinkedContributors(...args),
    getAssignableGroups: (...args: unknown[]) => getAssignableGroups(...args),
    issueRegistrationLink: (...args: unknown[]) =>
        issueRegistrationLink(...args),
}));

const toastAdd = vi.fn();
vi.mock('primevue/usetoast', () => ({
    useToast: () => ({ add: toastAdd }),
}));

import InviteContributor from './InviteContributor.vue';

// Minimal v-model-capable stand-ins for the PrimeVue widgets so state can be
// driven via $emit and the Button's disabled attribute can be read.
const vModelStub = (name: string, tag = 'div') =>
    defineComponent({
        name,
        props: {
            modelValue: { type: [String, Array, Boolean], default: null },
        },
        emits: ['update:modelValue'],
        template: `<${tag}></${tag}>`,
    });

// Reflects the bound value so readonly result fields can be asserted.
const InputTextStub = defineComponent({
    name: 'InputText',
    props: { modelValue: { type: String, default: '' } },
    emits: ['update:modelValue'],
    template: `<input :value="modelValue" />`,
});

const ButtonStub = defineComponent({
    name: 'PvButton',
    props: {
        disabled: { type: Boolean, default: false },
        label: { type: String, default: '' },
        loading: { type: Boolean, default: false },
    },
    emits: ['click'],
    template: `<button :disabled="disabled" @click="$emit('click')">{{ label }}</button>`,
});

function mountInvite() {
    return mount(InviteContributor, {
        global: {
            stubs: {
                Button: ButtonStub,
                Select: vModelStub('Select'),
                MultiSelect: vModelStub('MultiSelect'),
                Checkbox: vModelStub('Checkbox', 'input'),
                SelectButton: vModelStub('SelectButton'),
                InputText: InputTextStub,
            },
        },
    });
}

const setContributor = (w: ReturnType<typeof mountInvite>, id: string) =>
    w.findComponent({ name: 'Select' }).vm.$emit('update:modelValue', id);

const setGroups = (w: ReturnType<typeof mountInvite>, groups: string[]) =>
    w
        .findComponent({ name: 'MultiSelect' })
        .vm.$emit('update:modelValue', groups);

beforeEach(() => {
    vi.clearAllMocks();
    getUnlinkedContributors.mockResolvedValue([]);
    getAssignableGroups.mockResolvedValue(['Submitter', 'Permit Decider']);
});

describe('on mount', () => {
    it('loads contributors and assignable groups', async () => {
        mountInvite();
        await flushPromises();
        expect(getUnlinkedContributors).toHaveBeenCalled();
        expect(getAssignableGroups).toHaveBeenCalled();
    });

    it('shows an inline error when loading fails', async () => {
        getAssignableGroups.mockRejectedValue(new Error('Boom'));
        const wrapper = mountInvite();
        await flushPromises();
        expect(wrapper.find('.error-msg').text()).toBe('Boom');
    });
});

describe('submit gating (existing contributor)', () => {
    it('disables the button until a contributor and groups are set', async () => {
        const wrapper = mountInvite();
        await flushPromises();
        const button = () =>
            wrapper.find<HTMLButtonElement>('button').element.disabled;

        expect(button()).toBe(true);

        await setGroups(wrapper, ['Permit Decider']);
        // groups alone is not enough without a contributor
        expect(button()).toBe(true);

        await setContributor(wrapper, 'contrib-1');
        expect(button()).toBe(false);
    });
});

describe('external applicant', () => {
    it('pins groups to Submitter when checked', async () => {
        const wrapper = mountInvite();
        await flushPromises();

        await wrapper
            .findComponent({ name: 'Checkbox' })
            .vm.$emit('update:modelValue', true);
        await flushPromises();

        expect(
            wrapper.findComponent({ name: 'MultiSelect' }).props('modelValue'),
        ).toEqual(['Submitter']);
    });
});

describe('submit', () => {
    it('renders the signup link on success', async () => {
        issueRegistrationLink.mockResolvedValue({
            signup_url: 'https://example.test/claim?token=abc',
            expires: '2030-01-01T00:00:00Z',
        });
        const wrapper = mountInvite();
        await flushPromises();
        await setGroups(wrapper, ['Permit Decider']);
        await setContributor(wrapper, 'contrib-1');

        await wrapper.find('button').trigger('click');
        await flushPromises();

        expect(wrapper.find('.result').exists()).toBe(true);
        expect(
            wrapper.find<HTMLInputElement>('.result input').element.value,
        ).toBe('https://example.test/claim?token=abc');
    });

    it('shows the error message inline, not as a toast', async () => {
        issueRegistrationLink.mockRejectedValue(
            new Error('Enter a valid email address.'),
        );
        const wrapper = mountInvite();
        await flushPromises();
        await setGroups(wrapper, ['Permit Decider']);
        await setContributor(wrapper, 'contrib-1');

        await wrapper.find('button').trigger('click');
        await flushPromises();

        expect(wrapper.find('.error-msg').text()).toBe(
            'Enter a valid email address.',
        );
        expect(toastAdd).not.toHaveBeenCalled();
    });
});
