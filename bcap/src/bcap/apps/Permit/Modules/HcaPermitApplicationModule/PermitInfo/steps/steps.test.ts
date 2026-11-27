import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ref } from 'vue';
import type { Ref } from 'vue';
import { shallowMount, config } from '@vue/test-utils';

import Step1 from './Step1_Contacts.vue';
import Step2 from './Step2_Overview.vue';

config.global.renderStubDefaultSlot = true;

vi.mock('@/arches_vue_components/widgets/constants.ts', () => ({
    EDIT: 'edit',
    VIEW: 'view',
}));

vi.mock('@/bcap/client/zod.gen.ts', () => ({
    zNonLocalizedStringAliasedNodeData: {},
    zReferenceAliasedNodeData: {},
}));

const { draftStepContainer } = vi.hoisted(() => ({
    draftStepContainer: {
        typedDraftData: null as Ref<Record<string, unknown>> | null,
    },
}));

// Assigned at module level after imports are resolved (vi.hoisted runs before
// imports, so ref() cannot be called inside it).
draftStepContainer.typedDraftData = ref<Record<string, unknown>>({});

vi.mock('@/bcap/composables/useDraftStep.ts', () => ({
    useDraftStep: () => ({
        draftData: ref({}),
        typedDraftData: draftStepContainer.typedDraftData,
        resolver: vi.fn(),
        isValid: vi.fn(() => true),
        updateValue: vi.fn(),
    }),
}));

const globalMountOptions = {
    global: {
        stubs: {
            FieldSet: { template: '<div><slot/></div>' },
            Fieldset: { template: '<div><slot/></div>' },
            Form: {
                template: '<form><slot/></form>',
                methods: { reset: () => {} },
            },
            GenericWidget: {
                name: 'GenericWidget',
                template: '<div class="mock-widget"></div>',
                props: ['nodeAlias'],
            },
        },
    },
};

const widgetAliases = (wrapper: ReturnType<typeof shallowMount>): string[] =>
    wrapper
        .findAllComponents({ name: 'GenericWidget' })
        .map((w) => w.props('nodeAlias') as string);

const steps = { Step1, Step2 };

describe('PermitInfo steps', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        draftStepContainer.typedDraftData.value = {};
    });

    for (const [name, component] of Object.entries(steps)) {
        it(`${name} renders and exposes isValid()`, () => {
            const wrapper = shallowMount(component, globalMountOptions);
            expect(wrapper.html()).toBeTruthy();
            expect(
                typeof (
                    wrapper.vm as unknown as { isValid: () => boolean }
                ).isValid(),
            ).toBe('boolean');
        });
    }

    describe('Step2 Overview conditionals', () => {
        it('shows existing_permit_number when is_replacement_permit is true', () => {
            draftStepContainer.typedDraftData.value = {
                application_overview: {
                    aliased_data: {
                        is_replacement_permit: { node_value: true },
                    },
                },
            };
            const wrapper = shallowMount(Step2, globalMountOptions);
            expect(widgetAliases(wrapper)).toContain('existing_permit_number');
        });

        it('hides existing_permit_number when is_replacement_permit is false', () => {
            draftStepContainer.typedDraftData.value = {
                application_overview: {
                    aliased_data: {
                        is_replacement_permit: { node_value: false },
                    },
                },
            };
            const wrapper = shallowMount(Step2, globalMountOptions);
            expect(widgetAliases(wrapper)).not.toContain(
                'existing_permit_number',
            );
        });

        it('shows concurrent_permit_numbers when has_concurrent_permits is true', () => {
            draftStepContainer.typedDraftData.value = {
                application_overview: {
                    aliased_data: {
                        has_concurrent_permits: { node_value: true },
                    },
                },
            };
            const wrapper = shallowMount(Step2, globalMountOptions);
            expect(widgetAliases(wrapper)).toContain(
                'concurrent_permit_numbers',
            );
        });

        it('hides concurrent_permit_numbers when has_concurrent_permits is false', () => {
            draftStepContainer.typedDraftData.value = {
                application_overview: {
                    aliased_data: {
                        has_concurrent_permits: { node_value: false },
                    },
                },
            };
            const wrapper = shallowMount(Step2, globalMountOptions);
            expect(widgetAliases(wrapper)).not.toContain(
                'concurrent_permit_numbers',
            );
        });

        it('shows other_permit_term when standard_permit_term is false', () => {
            draftStepContainer.typedDraftData.value = {
                application_overview: {
                    aliased_data: {
                        standard_permit_term: { node_value: false },
                    },
                },
            };
            const wrapper = shallowMount(Step2, globalMountOptions);
            expect(widgetAliases(wrapper)).toContain('other_permit_term');
        });

        it('hides other_permit_term when standard_permit_term is true', () => {
            draftStepContainer.typedDraftData.value = {
                application_overview: {
                    aliased_data: {
                        standard_permit_term: { node_value: true },
                    },
                },
            };
            const wrapper = shallowMount(Step2, globalMountOptions);
            expect(widgetAliases(wrapper)).not.toContain('other_permit_term');
        });
    });
});
