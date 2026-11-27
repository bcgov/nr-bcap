import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ref } from 'vue';
import type { Ref } from 'vue';
import { shallowMount, config } from '@vue/test-utils';

import Step1 from './Step1_About.vue';
import Step2 from './Step2_ProjectDetails.vue';
import Step3 from './Step3_AffectedSites.vue';
import Step4 from './Step4_RelatedAssessments.vue';
import Step5 from './Step5_ImpactManagement.vue';
import Step6 from './Step6_PermitsDiscussion.vue';

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

const steps = { Step1, Step2, Step3, Step4, Step5, Step6 };

describe('PermitScopeAlteration steps', () => {
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

    describe('Step3 AffectedSites rows', () => {
        it('renders two widgets per affected site tile', () => {
            draftStepContainer.typedDraftData!.value = {
                permit_scope: {
                    aliased_data: {
                        permit_scope_alteration: {
                            aliased_data: {
                                affected_archaeological_site: [
                                    { aliased_data: {} },
                                    { aliased_data: {} },
                                ],
                            },
                        },
                    },
                },
            };
            const wrapper = shallowMount(Step3, globalMountOptions);
            const aliases = widgetAliases(wrapper);
            expect(
                aliases.filter((a) => a === 'affected_archaeological_site'),
            ).toHaveLength(2);
            expect(
                aliases.filter((a) => a === 'anticipated_impacts'),
            ).toHaveLength(2);
        });
    });

    describe('Step4 RelatedAssessments rows', () => {
        it('renders five widgets per related assessment tile', () => {
            draftStepContainer.typedDraftData!.value = {
                permit_scope: {
                    aliased_data: {
                        permit_scope_alteration: {
                            aliased_data: {
                                related_assessment: [
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
            expect(aliases.filter((a) => a === 'study_type')).toHaveLength(2);
            expect(
                aliases.filter((a) => a === 'assessment_comments'),
            ).toHaveLength(2);
        });
    });

    describe('Step5 ImpactManagement conditionals', () => {
        it('shows stockpile_plan_approach when stockpile_plan_required is true', () => {
            draftStepContainer.typedDraftData!.value = {
                permit_scope: {
                    aliased_data: {
                        permit_scope_alteration: {
                            aliased_data: {
                                stockpile_plan_required: { node_value: true },
                            },
                        },
                    },
                },
            };
            const wrapper = shallowMount(Step5, globalMountOptions);
            expect(widgetAliases(wrapper)).toContain('stockpile_plan_approach');
        });

        it('hides stockpile_plan_approach when stockpile_plan_required is false', () => {
            draftStepContainer.typedDraftData!.value = {
                permit_scope: {
                    aliased_data: {
                        permit_scope_alteration: {
                            aliased_data: {
                                stockpile_plan_required: { node_value: false },
                            },
                        },
                    },
                },
            };
            const wrapper = shallowMount(Step5, globalMountOptions);
            expect(widgetAliases(wrapper)).not.toContain(
                'stockpile_plan_approach',
            );
        });
    });

    describe('Step6 PermitsDiscussion conditionals', () => {
        it('shows related_permits_description when has_related_permits is true', () => {
            draftStepContainer.typedDraftData!.value = {
                permit_scope: {
                    aliased_data: {
                        permit_scope_alteration: {
                            aliased_data: {
                                has_related_permits: { node_value: true },
                            },
                        },
                    },
                },
            };
            const wrapper = shallowMount(Step6, globalMountOptions);
            expect(widgetAliases(wrapper)).toContain(
                'related_permits_description',
            );
        });

        it('hides related_permits_description when has_related_permits is false', () => {
            draftStepContainer.typedDraftData!.value = {
                permit_scope: {
                    aliased_data: {
                        permit_scope_alteration: {
                            aliased_data: {
                                has_related_permits: { node_value: false },
                            },
                        },
                    },
                },
            };
            const wrapper = shallowMount(Step6, globalMountOptions);
            expect(widgetAliases(wrapper)).not.toContain(
                'related_permits_description',
            );
        });
    });
});
