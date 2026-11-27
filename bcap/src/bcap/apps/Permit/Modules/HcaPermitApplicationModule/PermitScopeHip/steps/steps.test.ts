import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ref } from 'vue';
import type { Ref } from 'vue';
import { shallowMount, config } from '@vue/test-utils';

import Step1 from './Step1_About.vue';
import Step2 from './Step2_ProposedDevelopment.vue';
import Step3 from './Step3_Objectives.vue';
import Step4 from './Step4_ArchaeologicalStudies.vue';
import Step5 from './Step5_AlterationsDiscussion.vue';

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

const steps = { Step1, Step2, Step3, Step4, Step5 };

describe('PermitScopeHip steps', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        draftStepContainer.typedDraftData!.value = {};
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

    describe('Step2 ProposedDevelopment conditionals', () => {
        it('shows hip_assessment_area_size_ha when application area type is Single Development', () => {
            draftStepContainer.typedDraftData!.value = {
                permit_scope: {
                    aliased_data: {
                        permit_scope_hip: {
                            aliased_data: {
                                hip_application_area_type: {
                                    node_value: [
                                        {
                                            uri: 'https://localhost/bcap/ea010001-0000-4000-8000-000000000001',
                                        },
                                    ],
                                },
                            },
                        },
                    },
                },
            };
            const wrapper = shallowMount(Step2, globalMountOptions);
            expect(widgetAliases(wrapper)).toContain(
                'hip_assessment_area_size_ha',
            );
        });

        it('hides hip_assessment_area_size_ha when application area type is MAP', () => {
            draftStepContainer.typedDraftData!.value = {
                permit_scope: {
                    aliased_data: {
                        permit_scope_hip: {
                            aliased_data: {
                                hip_application_area_type: {
                                    node_value: [
                                        {
                                            uri: 'https://localhost/bcap/ea010002-0000-4000-8000-000000000002',
                                        },
                                    ],
                                },
                            },
                        },
                    },
                },
            };
            const wrapper = shallowMount(Step2, globalMountOptions);
            expect(widgetAliases(wrapper)).not.toContain(
                'hip_assessment_area_size_ha',
            );
        });

        it('shows hip_development_selection when application area type is MAP', () => {
            draftStepContainer.typedDraftData!.value = {
                permit_scope: {
                    aliased_data: {
                        permit_scope_hip: {
                            aliased_data: {
                                hip_application_area_type: {
                                    node_value: [
                                        {
                                            uri: 'https://localhost/bcap/ea010002-0000-4000-8000-000000000002',
                                        },
                                    ],
                                },
                            },
                        },
                    },
                },
            };
            const wrapper = shallowMount(Step2, globalMountOptions);
            expect(widgetAliases(wrapper)).toContain(
                'hip_development_selection',
            );
        });

        it('hides hip_development_selection when application area type is Single Development', () => {
            draftStepContainer.typedDraftData!.value = {
                permit_scope: {
                    aliased_data: {
                        permit_scope_hip: {
                            aliased_data: {
                                hip_application_area_type: {
                                    node_value: [
                                        {
                                            uri: 'https://localhost/bcap/ea010001-0000-4000-8000-000000000001',
                                        },
                                    ],
                                },
                            },
                        },
                    },
                },
            };
            const wrapper = shallowMount(Step2, globalMountOptions);
            expect(widgetAliases(wrapper)).not.toContain(
                'hip_development_selection',
            );
        });

        it('shows hip_chance_finds_details when hip_addresses_chance_finds is true', () => {
            draftStepContainer.typedDraftData!.value = {
                permit_scope: {
                    aliased_data: {
                        permit_scope_hip: {
                            aliased_data: {
                                hip_addresses_chance_finds: {
                                    node_value: true,
                                },
                            },
                        },
                    },
                },
            };
            const wrapper = shallowMount(Step2, globalMountOptions);
            expect(widgetAliases(wrapper)).toContain(
                'hip_chance_finds_details',
            );
        });

        it('hides hip_chance_finds_details when hip_addresses_chance_finds is false', () => {
            draftStepContainer.typedDraftData!.value = {
                permit_scope: {
                    aliased_data: {
                        permit_scope_hip: {
                            aliased_data: {
                                hip_addresses_chance_finds: {
                                    node_value: false,
                                },
                            },
                        },
                    },
                },
            };
            const wrapper = shallowMount(Step2, globalMountOptions);
            expect(widgetAliases(wrapper)).not.toContain(
                'hip_chance_finds_details',
            );
        });
    });

    describe('Step3 Objectives conditionals', () => {
        it('shows hip_objectives_non_alignment when hip_confirms_objectives_align is false', () => {
            draftStepContainer.typedDraftData!.value = {
                permit_scope: {
                    aliased_data: {
                        permit_scope_hip: {
                            aliased_data: {
                                hip_confirms_objectives_align: {
                                    node_value: false,
                                },
                            },
                        },
                    },
                },
            };
            const wrapper = shallowMount(Step3, globalMountOptions);
            expect(widgetAliases(wrapper)).toContain(
                'hip_objectives_non_alignment',
            );
        });

        it('hides hip_objectives_non_alignment when hip_confirms_objectives_align is true', () => {
            draftStepContainer.typedDraftData!.value = {
                permit_scope: {
                    aliased_data: {
                        permit_scope_hip: {
                            aliased_data: {
                                hip_confirms_objectives_align: {
                                    node_value: true,
                                },
                            },
                        },
                    },
                },
            };
            const wrapper = shallowMount(Step3, globalMountOptions);
            expect(widgetAliases(wrapper)).not.toContain(
                'hip_objectives_non_alignment',
            );
        });
    });

    describe('Step4 ArchaeologicalStudies conditionals', () => {
        it('shows AOA sub-fields when hip_has_aoa is true', () => {
            draftStepContainer.typedDraftData!.value = {
                permit_scope: {
                    aliased_data: {
                        permit_scope_hip: {
                            aliased_data: {
                                hip_has_aoa: { node_value: true },
                            },
                        },
                    },
                },
            };
            const wrapper = shallowMount(Step4, globalMountOptions);
            const aliases = widgetAliases(wrapper);
            expect(aliases).toContain('hip_has_predictive_model');
            expect(aliases).toContain('hip_has_desk_based_assessment');
            expect(aliases).toContain('hip_was_hip_aoa_permitted');
        });

        it('hides AOA sub-fields when hip_has_aoa is false', () => {
            draftStepContainer.typedDraftData!.value = {
                permit_scope: {
                    aliased_data: {
                        permit_scope_hip: {
                            aliased_data: {
                                hip_has_aoa: { node_value: false },
                            },
                        },
                    },
                },
            };
            const wrapper = shallowMount(Step4, globalMountOptions);
            const aliases = widgetAliases(wrapper);
            expect(aliases).not.toContain('hip_has_predictive_model');
            expect(aliases).not.toContain('hip_has_desk_based_assessment');
            expect(aliases).not.toContain('hip_was_hip_aoa_permitted');
        });

        it('shows hip_predictive_model_name when hip_has_predictive_model is true', () => {
            draftStepContainer.typedDraftData!.value = {
                permit_scope: {
                    aliased_data: {
                        permit_scope_hip: {
                            aliased_data: {
                                hip_has_aoa: { node_value: true },
                                hip_has_predictive_model: { node_value: true },
                            },
                        },
                    },
                },
            };
            const wrapper = shallowMount(Step4, globalMountOptions);
            expect(widgetAliases(wrapper)).toContain(
                'hip_predictive_model_name',
            );
        });

        it('hides hip_predictive_model_name when hip_has_predictive_model is false', () => {
            draftStepContainer.typedDraftData!.value = {
                permit_scope: {
                    aliased_data: {
                        permit_scope_hip: {
                            aliased_data: {
                                hip_has_aoa: { node_value: true },
                                hip_has_predictive_model: { node_value: false },
                            },
                        },
                    },
                },
            };
            const wrapper = shallowMount(Step4, globalMountOptions);
            expect(widgetAliases(wrapper)).not.toContain(
                'hip_predictive_model_name',
            );
        });

        it('renders four widgets per previous studies tile', () => {
            draftStepContainer.typedDraftData!.value = {
                permit_scope: {
                    aliased_data: {
                        permit_scope_hip: {
                            aliased_data: {
                                hip_previous_studies: [
                                    { aliased_data: {} },
                                    { aliased_data: {} },
                                ],
                            },
                        },
                    },
                },
            };
            const wrapper = shallowMount(Step4, globalMountOptions);
            const aliases = widgetAliases(wrapper);
            // 4 tiles fields per study × 2 studies = 8, plus the 3 always-visible study checkboxes
            expect(aliases.filter((a) => a === 'hip_study_title')).toHaveLength(
                2,
            );
            expect(
                aliases.filter((a) => a === 'hip_study_comments'),
            ).toHaveLength(2);
        });

        it('renders one widget per recorded site tile', () => {
            draftStepContainer.typedDraftData!.value = {
                permit_scope: {
                    aliased_data: {
                        permit_scope_hip: {
                            aliased_data: {
                                hip_recorded_archaeological_sites: [
                                    { aliased_data: {} },
                                    { aliased_data: {} },
                                    { aliased_data: {} },
                                ],
                            },
                        },
                    },
                },
            };
            const wrapper = shallowMount(Step4, globalMountOptions);
            const aliases = widgetAliases(wrapper);
            expect(
                aliases.filter((a) => a === 'hip_archaeological_site'),
            ).toHaveLength(3);
        });
    });

    describe('Step5 AlterationsDiscussion conditionals', () => {
        it('shows hip_alteration_type when hip_has_related_alterations is true', () => {
            draftStepContainer.typedDraftData!.value = {
                permit_scope: {
                    aliased_data: {
                        permit_scope_hip: {
                            aliased_data: {
                                hip_has_related_alterations: {
                                    node_value: true,
                                },
                            },
                        },
                    },
                },
            };
            const wrapper = shallowMount(Step5, globalMountOptions);
            expect(widgetAliases(wrapper)).toContain('hip_alteration_type');
        });

        it('hides hip_alteration_type when hip_has_related_alterations is false', () => {
            draftStepContainer.typedDraftData!.value = {
                permit_scope: {
                    aliased_data: {
                        permit_scope_hip: {
                            aliased_data: {
                                hip_has_related_alterations: {
                                    node_value: false,
                                },
                            },
                        },
                    },
                },
            };
            const wrapper = shallowMount(Step5, globalMountOptions);
            expect(widgetAliases(wrapper)).not.toContain('hip_alteration_type');
        });
    });
});
