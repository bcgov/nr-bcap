import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ref } from 'vue';
import type { Ref } from 'vue';
import { shallowMount, config } from '@vue/test-utils';

import Step1 from './Step1_ResearchDesign.vue';
import Step2 from './Step2_SurveyCoverage.vue';
import Step3 from './Step3_SubsurfaceTesting.vue';
import Step4 from './Step4_MachineAssistedMethods.vue';
import Step5 from './Step5_WinterMethods.vue';
import Step6 from './Step6_OtherFieldMethods.vue';

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

const steps = { Step1, Step2, Step3, Step4, Step5, Step6 };

describe('ArchMethods steps', () => {
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

    describe('Step1 ResearchDesign conditionals', () => {
        it('shows methods_non_alignment when confirms_methods_align is false', () => {
            draftStepContainer.typedDraftData.value = {
                methodology: {
                    aliased_data: {
                        confirms_methods_align: { node_value: false },
                    },
                },
            };
            const wrapper = shallowMount(Step1, globalMountOptions);
            expect(widgetAliases(wrapper)).toContain('methods_non_alignment');
        });

        it('hides methods_non_alignment when confirms_methods_align is true', () => {
            draftStepContainer.typedDraftData.value = {
                methodology: {
                    aliased_data: {
                        confirms_methods_align: { node_value: true },
                    },
                },
            };
            const wrapper = shallowMount(Step1, globalMountOptions);
            expect(widgetAliases(wrapper)).not.toContain(
                'methods_non_alignment',
            );
        });

        it('shows pre_field_research_non_alignment when confirms_pre_field_research_aligns is false', () => {
            draftStepContainer.typedDraftData.value = {
                methodology: {
                    aliased_data: {
                        confirms_pre_field_research_aligns: {
                            node_value: false,
                        },
                    },
                },
            };
            const wrapper = shallowMount(Step1, globalMountOptions);
            expect(widgetAliases(wrapper)).toContain(
                'pre_field_research_non_alignment',
            );
        });

        it('hides pre_field_research_non_alignment when confirms_pre_field_research_aligns is true', () => {
            draftStepContainer.typedDraftData.value = {
                methodology: {
                    aliased_data: {
                        confirms_pre_field_research_aligns: {
                            node_value: true,
                        },
                    },
                },
            };
            const wrapper = shallowMount(Step1, globalMountOptions);
            expect(widgetAliases(wrapper)).not.toContain(
                'pre_field_research_non_alignment',
            );
        });
    });

    describe('Step2 SurveyCoverage conditionals', () => {
        it('shows non-alignment widgets when both align booleans are false', () => {
            draftStepContainer.typedDraftData.value = {
                methodology: {
                    aliased_data: {
                        confirms_survey_coverage_aligns: { node_value: false },
                        confirms_arch_potential_aligns: { node_value: false },
                    },
                },
            };
            const wrapper = shallowMount(Step2, globalMountOptions);
            const aliases = widgetAliases(wrapper);
            expect(aliases).toContain('survey_coverage_non_alignment');
            expect(aliases).toContain('arch_potential_non_alignment');
        });

        it('hides non-alignment widgets when align booleans are true', () => {
            draftStepContainer.typedDraftData.value = {
                methodology: {
                    aliased_data: {
                        confirms_survey_coverage_aligns: { node_value: true },
                        confirms_arch_potential_aligns: { node_value: true },
                    },
                },
            };
            const wrapper = shallowMount(Step2, globalMountOptions);
            const aliases = widgetAliases(wrapper);
            expect(aliases).not.toContain('survey_coverage_non_alignment');
            expect(aliases).not.toContain('arch_potential_non_alignment');
        });
    });

    describe('Step3 SubsurfaceTesting conditionals', () => {
        it('shows subsurface_testing_non_alignment when align is false', () => {
            draftStepContainer.typedDraftData.value = {
                methodology: {
                    aliased_data: {
                        confirms_subsurface_testing_aligns: {
                            node_value: false,
                        },
                    },
                },
            };
            const wrapper = shallowMount(Step3, globalMountOptions);
            expect(widgetAliases(wrapper)).toContain(
                'subsurface_testing_non_alignment',
            );
        });

        it('hides subsurface_testing_non_alignment when align is true', () => {
            draftStepContainer.typedDraftData.value = {
                methodology: {
                    aliased_data: {
                        confirms_subsurface_testing_aligns: {
                            node_value: true,
                        },
                    },
                },
            };
            const wrapper = shallowMount(Step3, globalMountOptions);
            expect(widgetAliases(wrapper)).not.toContain(
                'subsurface_testing_non_alignment',
            );
        });
    });

    describe('Step4 MachineAssistedMethods conditionals', () => {
        it('shows child fields when has_machine_assisted_methods is true', () => {
            draftStepContainer.typedDraftData.value = {
                methodology: {
                    aliased_data: {
                        has_machine_assisted_methods: { node_value: true },
                    },
                },
            };
            const wrapper = shallowMount(Step4, globalMountOptions);
            const aliases = widgetAliases(wrapper);
            expect(aliases).toContain('machine_assisted_methods_description');
            expect(aliases).toContain('machine_assisted_approach');
        });

        it('hides child fields when has_machine_assisted_methods is false', () => {
            draftStepContainer.typedDraftData.value = {
                methodology: {
                    aliased_data: {
                        has_machine_assisted_methods: { node_value: false },
                    },
                },
            };
            const wrapper = shallowMount(Step4, globalMountOptions);
            expect(widgetAliases(wrapper)).not.toContain(
                'machine_assisted_methods_description',
            );
        });
    });

    describe('Step5 WinterMethods conditionals', () => {
        it('shows winter fields when has_winter_methods is true', () => {
            draftStepContainer.typedDraftData.value = {
                methodology: {
                    aliased_data: {
                        has_winter_methods: { node_value: true },
                    },
                },
            };
            const wrapper = shallowMount(Step5, globalMountOptions);
            const aliases = widgetAliases(wrapper);
            expect(aliases).toContain('winter_methods_align');
            expect(aliases).toContain('winter_methods_description');
        });

        it('hides winter fields when has_winter_methods is false', () => {
            draftStepContainer.typedDraftData.value = {
                methodology: {
                    aliased_data: {
                        has_winter_methods: { node_value: false },
                    },
                },
            };
            const wrapper = shallowMount(Step5, globalMountOptions);
            const aliases = widgetAliases(wrapper);
            expect(aliases).not.toContain('winter_methods_align');
            expect(aliases).not.toContain('winter_methods_non_alignment');
        });

        it('shows winter_methods_non_alignment when has_winter_methods is true and winter_methods_align is false', () => {
            draftStepContainer.typedDraftData.value = {
                methodology: {
                    aliased_data: {
                        has_winter_methods: { node_value: true },
                        winter_methods_align: { node_value: false },
                    },
                },
            };
            const wrapper = shallowMount(Step5, globalMountOptions);
            expect(widgetAliases(wrapper)).toContain(
                'winter_methods_non_alignment',
            );
        });

        it('hides winter_methods_non_alignment when winter_methods_align is true', () => {
            draftStepContainer.typedDraftData.value = {
                methodology: {
                    aliased_data: {
                        has_winter_methods: { node_value: true },
                        winter_methods_align: { node_value: true },
                    },
                },
            };
            const wrapper = shallowMount(Step5, globalMountOptions);
            expect(widgetAliases(wrapper)).not.toContain(
                'winter_methods_non_alignment',
            );
        });
    });
});
