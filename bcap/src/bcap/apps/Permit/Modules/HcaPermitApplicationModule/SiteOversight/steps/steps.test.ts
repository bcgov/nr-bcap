import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ref } from 'vue';
import type { Ref } from 'vue';
import { shallowMount, config } from '@vue/test-utils';

import Step1 from './Step1_About.vue';
import Step2 from './Step2_Personnel.vue';
import Step3 from './Step3_OversightTable.vue';

config.global.renderStubDefaultSlot = true;

vi.mock('@/arches_vue_components/widgets/constants.ts', () => ({
    EDIT: 'edit',
    VIEW: 'view',
}));

const { draftStepContainer } = vi.hoisted(() => ({
    draftStepContainer: {
        typedDraftData: null as Ref<Record<string, unknown>> | null,
    },
}));

// Assigned at module level after imports are resolved (vi.hoisted runs before
// imports, so ref() cannot be called inside it).
draftStepContainer.typedDraftData = ref<Record<string, unknown>>({});

vi.mock(
    '@/arches_controlled_lists/stores/useReferenceSelectOptionsStore.ts',
    () => ({
        useReferenceSelectOptionsStore: () => ({
            fetchWidgetOptions: vi.fn(() => Promise.resolve([])),
        }),
    }),
);

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
            MultiSelect: {
                name: 'MultiSelect',
                template: '<div class="mock-multiselect"></div>',
                props: ['modelValue', 'options'],
            },
        },
    },
};

const widgetAliases = (wrapper: ReturnType<typeof shallowMount>): string[] =>
    wrapper
        .findAllComponents({ name: 'GenericWidget' })
        .map((w) => w.props('nodeAlias') as string);

const steps = { Step1, Step2, Step3 };

describe('SiteOversight steps', () => {
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

    describe('Step2 Personnel conditionals', () => {
        it('shows archaeologist_deliverables_role when has_directing_archaeologist is true', () => {
            draftStepContainer.typedDraftData.value = {
                personnel: {
                    aliased_data: {
                        has_directing_archaeologist: { node_value: true },
                    },
                },
            };
            const wrapper = shallowMount(Step2, globalMountOptions);
            expect(widgetAliases(wrapper)).toContain(
                'archaeologist_deliverables_role',
            );
        });

        it('hides archaeologist_deliverables_role when has_directing_archaeologist is false', () => {
            draftStepContainer.typedDraftData.value = {
                personnel: {
                    aliased_data: {
                        has_directing_archaeologist: { node_value: false },
                    },
                },
            };
            const wrapper = shallowMount(Step2, globalMountOptions);
            expect(widgetAliases(wrapper)).not.toContain(
                'archaeologist_deliverables_role',
            );
        });

        it('shows applicant_responsibility_details when has_directing_archaeologist is false', () => {
            draftStepContainer.typedDraftData.value = {
                personnel: {
                    aliased_data: {
                        has_directing_archaeologist: { node_value: false },
                    },
                },
            };
            const wrapper = shallowMount(Step2, globalMountOptions);
            expect(widgetAliases(wrapper)).toContain(
                'applicant_responsibility_details',
            );
        });

        it('hides applicant_responsibility_details when has_directing_archaeologist is true', () => {
            draftStepContainer.typedDraftData.value = {
                personnel: {
                    aliased_data: {
                        has_directing_archaeologist: { node_value: true },
                    },
                },
            };
            const wrapper = shallowMount(Step2, globalMountOptions);
            expect(widgetAliases(wrapper)).not.toContain(
                'applicant_responsibility_details',
            );
        });

        it('shows neither conditional field when has_directing_archaeologist is unset', () => {
            draftStepContainer.typedDraftData.value = {};
            const wrapper = shallowMount(Step2, globalMountOptions);
            const aliases = widgetAliases(wrapper);
            expect(aliases).not.toContain('archaeologist_deliverables_role');
            expect(aliases).not.toContain('applicant_responsibility_details');
        });
    });

    describe('Step3 OversightTable conditionals', () => {
        it('shows one responsible_person widget per cultural area tile', () => {
            draftStepContainer.typedDraftData.value = {
                personnel: {
                    aliased_data: {
                        assessment_oversight_responsibility: [
                            {
                                aliased_data: {
                                    cultural_area: {
                                        node_value: [
                                            {
                                                uri: 'https://localhost/bcap/ee010002-0000-4000-8000-000000000002',
                                            },
                                        ],
                                    },
                                },
                            },
                        ],
                    },
                },
            };
            const wrapper = shallowMount(Step3, globalMountOptions);
            const aliases = widgetAliases(wrapper);
            expect(aliases).toContain('responsible_person');
            expect(aliases).not.toContain('responsibility_role');
            expect(
                aliases.filter((a) => a === 'responsible_person'),
            ).toHaveLength(1);
        });

        it('shows one widget per cultural area tile when multiple tiles are present', () => {
            draftStepContainer.typedDraftData.value = {
                personnel: {
                    aliased_data: {
                        assessment_oversight_responsibility: [
                            {
                                aliased_data: {
                                    cultural_area: {
                                        node_value: [
                                            {
                                                uri: 'https://localhost/bcap/ee010002-0000-4000-8000-000000000002',
                                            },
                                        ],
                                    },
                                },
                            },
                            {
                                aliased_data: {
                                    cultural_area: {
                                        node_value: [
                                            {
                                                uri: 'https://localhost/bcap/ee010003-0000-4000-8000-000000000003',
                                            },
                                        ],
                                    },
                                },
                            },
                        ],
                    },
                },
            };
            const wrapper = shallowMount(Step3, globalMountOptions);
            expect(
                wrapper.findAllComponents({ name: 'GenericWidget' }),
            ).toHaveLength(2);
        });

        it('shows no oversight widgets when no tiles are present', () => {
            draftStepContainer.typedDraftData.value = {
                personnel: {
                    aliased_data: {
                        assessment_oversight_responsibility: [],
                    },
                },
            };
            const wrapper = shallowMount(Step3, globalMountOptions);
            const aliases = widgetAliases(wrapper);
            expect(aliases).not.toContain('responsible_person');
            expect(aliases).not.toContain('responsibility_role');
        });

        it('shows responsible_person for delegated tiles (no cultural_area)', () => {
            draftStepContainer.typedDraftData.value = {
                personnel: {
                    aliased_data: {
                        assessment_oversight_responsibility: [
                            { aliased_data: {} },
                            { aliased_data: {} },
                        ],
                    },
                },
            };
            const wrapper = shallowMount(Step3, globalMountOptions);
            expect(
                wrapper
                    .findAllComponents({ name: 'GenericWidget' })
                    .filter(
                        (w) => w.props('nodeAlias') === 'responsible_person',
                    ),
            ).toHaveLength(2);
        });

        it('separates cultural area and delegated tiles', () => {
            draftStepContainer.typedDraftData.value = {
                personnel: {
                    aliased_data: {
                        assessment_oversight_responsibility: [
                            {
                                aliased_data: {
                                    cultural_area: {
                                        node_value: [
                                            {
                                                uri: 'https://localhost/bcap/ee010002-0000-4000-8000-000000000002',
                                            },
                                        ],
                                    },
                                },
                            },
                            { aliased_data: {} },
                        ],
                    },
                },
            };
            const wrapper = shallowMount(Step3, globalMountOptions);
            expect(
                wrapper.findAllComponents({ name: 'GenericWidget' }),
            ).toHaveLength(2);
        });
    });
});
