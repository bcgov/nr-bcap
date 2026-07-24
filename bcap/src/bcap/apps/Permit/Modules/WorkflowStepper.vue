<script setup lang="ts">
import { computed, reactive, ref, onMounted } from 'vue';
import type { Component, Ref } from 'vue';
import { useDraftStore } from '@/bcap/stores/draft.ts';
import { useRoute } from 'vue-router';
import Stepper from 'primevue/stepper';
import Step from 'primevue/step';
import StepPanel from 'primevue/steppanel';
import StepList from 'primevue/steplist';
import StepPanels from 'primevue/steppanels';
import ProgressSpinner from 'primevue/progressspinner';
import StepperNavigation from '@/bcgov_arches_common/components/Stepper/components/StepperNavigation/StepperNavigation.vue';
import Panel from 'primevue/panel';
import type { StepperProps, StepperState } from 'primevue/stepper';
import Step99_Review from '@/bcap/apps/Permit/Modules/Step99_Review.vue';
import type { ErrorMessage } from '@/bcgov_arches_common/types.ts';
import type { ArchesDraftData } from '@/bcap/types.ts';
import type { PermitApplication } from '@/bcap/client/types.gen.ts';
import { submitModule, fetchDraft } from '@/bcap/apps/Permit/api.ts';
import { routeNames } from '@/bcap/apps/Permit/routes.ts';
import { GraphSlug } from '@/bcap/apps/Permit/graphSlug.ts';

// One content step: a nav-rail label, the component to render, and an optional
// panel heading (defaults to the label; pass '' to render no heading).
interface WorkflowStep {
    label: string;
    component: Component;
    heading?: string;
}

// A rendered step exposes isValid() so the shell can gate navigation.
interface StepInstance {
    isValid?: () => boolean;
}

const props = withDefaults(
    defineProps<{
        graphSlug: GraphSlug;
        title: string;
        steps: WorkflowStep[];
        submitLabel?: string;
        // How to persist on the final step. Defaults to the module-filing flow
        // (submitModule against the parent permit). The base permit application
        // has no parent, so it passes its own that calls submitApplication.
        submit?: () => Promise<PermitApplication | null>;
        // The Review/Submitted step body. Defaults to the generic summary of
        // every filled node; the base permit passes a curated version.
        reviewComponent?: Component;
    }>(),
    {
        submitLabel: 'Create Filing',
        reviewComponent: Step99_Review,
        submit: undefined,
    },
);

const defaultSubmit = async (): Promise<PermitApplication | null> => {
    if (!draft.draftId) throw new Error('No active draft found.');
    if (!draft.parentPermitId)
        throw new Error('No permit associated with this filing.');
    return submitModule(
        draft.parentPermitId,
        draft.draftId,
        props.graphSlug,
        draft.draftData,
    );
};

const route = useRoute();
const draft = useDraftStore();
// The permit this filing was started from. From the URL when starting fresh, or
// the loaded draft's parent_resource_id when resuming.
draft.initDraft(props.graphSlug, (route.query.permitId as string) ?? null);

const state = reactive({
    submissionErrors: [] as ErrorMessage[],
    submitted: false,
    submitting: false,
    devMode: true,
    isDataLoaded: false,
    finalizedResourceData: null as PermitApplication | null,
});

// The content steps plus the always-present Review and Submitted steps.
const reviewStepNumber = computed(() => props.steps.length + 1);
const totalSteps = computed(() => props.steps.length + 2);

// The filing summary to return to: the parent permit while filing a module, or
// the just-created permit on the base application's completion step.
const permitBackLink = computed(() => {
    const id =
        draft.parentPermitId ?? state.finalizedResourceData?.resourceinstanceid;
    return id ? { name: routeNames.permitDetails, params: { id } } : null;
});

const finalizedDataForReview = computed<ArchesDraftData | null>(() => {
    if (!state.finalizedResourceData?.aliased_data) return null;
    return state.finalizedResourceData
        .aliased_data as unknown as ArchesDraftData;
});

// Rendered step instances, indexed 0-based, for calling their isValid().
const stepEls = ref<StepInstance[]>([]);
const setStepRef = (index: number, el: unknown) => {
    stepEls.value[index] = (el as StepInstance) ?? {};
};

const stepStatuses: Ref<boolean[]> = ref([]);
const setCurrentStepValid = (isValid: boolean, stepNumber: number) => {
    stepStatuses.value[stepNumber - 1] = isValid;
};

const stepperProps: Ref<StepperProps | null> = ref(null);
const stepperState: Ref<StepperState | null> = ref(null);
const myStepper = ref();
let lastStep = 1;

const currentStep = computed(() => myStepper.value?.d_value);
const currentStepIsValid = computed(
    () => stepStatuses.value[currentStep.value - 1],
);

const stepIsValid = (step: number): boolean => {
    if (state.devMode) return true;
    const el = stepEls.value[step - 1];
    let valid = true;
    if (typeof el?.isValid === 'function') valid = el.isValid();
    if (step === totalSteps.value) state.submitted = true;
    return valid;
};

const submitFiling = async (): Promise<boolean> => {
    state.submitting = true;
    state.submissionErrors = [];
    try {
        const response = await (props.submit ?? defaultSubmit)();
        if (response) state.finalizedResourceData = response;
        return true;
    } catch (error) {
        console.error('Submission failed:', error);
        const message =
            error instanceof Error
                ? error.message
                : 'An unknown error occurred.';
        state.submissionErrors.push({
            type: 'Submission Error',
            error: 'Submission Failed',
            message,
        });
        return false;
    } finally {
        state.submitting = false;
    }
};

const print = () => window.print();

const activateNextStep = async () => {
    if (currentStep.value === totalSteps.value) {
        print();
    } else if (currentStep.value === totalSteps.value - 1) {
        const success = await submitFiling();
        if (success) {
            myStepper.value.d_value++;
            setCurrentStepValid(true, myStepper.value.d_value);
        }
    } else {
        myStepper.value.d_value++;
        setCurrentStepValid(
            stepIsValid(myStepper.value.d_value),
            myStepper.value.d_value,
        );
    }
};

const activatePreviousStep = () => {
    setCurrentStepValid(
        stepIsValid(myStepper.value.d_value - 1),
        myStepper.value.d_value - 1,
    );
    myStepper.value.d_value--;
};

const activateStep = (step: number) => {
    if (step > lastStep && !stepIsValid(lastStep)) {
        myStepper.value.d_value = lastStep;
    } else {
        lastStep = step;
        setCurrentStepValid(stepIsValid(step), step);
    }
};

const nextLabel = computed(() => {
    if (currentStep.value === totalSteps.value) return 'Print';
    return currentStep.value < totalSteps.value - 1
        ? 'Next'
        : props.submitLabel;
});

const showPrevious = computed(
    () => !(currentStep.value === totalSteps.value || currentStep.value === 1),
);

const headingFor = (step: WorkflowStep) => step.heading ?? step.label;

onMounted(async () => {
    try {
        // Only load an existing draft. A new one isn't created until the first
        // edit (store.ensureDraftId), so an abandoned form leaves no empty draft.
        const targetDraftId = route.query.draftId;
        if (targetDraftId) {
            const loaded = await fetchDraft(
                props.graphSlug,
                targetDraftId as string,
            );
            draft.loadDraft(loaded.id, (loaded.data || {}) as ArchesDraftData);
            draft.parentPermitId =
                loaded.parent_resource_id || draft.parentPermitId;
        }
        state.isDataLoaded = true;
    } catch (error) {
        console.error('Failed to initialize draft:', error);
        state.isDataLoaded = true;
    }
});
</script>

<template>
    <div
        v-if="state.submitting"
        class="submit-overlay"
    >
        <ProgressSpinner />
    </div>
    <Panel class="full-height">
        <div
            v-if="!state.isDataLoaded"
            style="display: flex; justify-content: center; padding: 3rem"
        >
            <ProgressSpinner />
        </div>

        <Stepper
            v-if="state.isDataLoaded"
            ref="myStepper"
            :state="stepperState"
            :props="stepperProps"
            :value="1"
            linear
            @update:value="activateStep"
        >
            <div class="bc-stepper-layout">
                <aside class="bc-stepper-nav">
                    <p class="bc-stepper-nav-label">Your progress</p>
                    <StepList>
                        <Step
                            v-for="(step, i) in steps"
                            :key="i"
                            :value="i + 1"
                        >
                            {{ step.label }}
                        </Step>
                        <Step :value="reviewStepNumber">Review Submission</Step>
                        <Step :value="totalSteps">Submission Complete</Step>
                    </StepList>
                </aside>
                <div class="bc-stepper-main">
                    <RouterLink
                        v-if="permitBackLink && currentStep === 1"
                        :to="permitBackLink"
                        class="back-to-permit"
                    >
                        <i class="fa-solid fa-chevron-left"></i>
                        Back to Filing Summary
                    </RouterLink>
                    <header class="bc-step-header">
                        <div>
                            <p class="bc-step-eyebrow">
                                Step {{ currentStep }} of {{ totalSteps }}
                            </p>
                            <h1 class="bc-step-title">{{ title }}</h1>
                        </div>
                        <StepperNavigation
                            :step-number="currentStep"
                            :is-valid="currentStepIsValid"
                            :show-previous="false"
                            :next-label="nextLabel"
                            @next-click="activateNextStep"
                            @previous-click="activatePreviousStep"
                        ></StepperNavigation>
                    </header>
                    <div
                        v-if="state.submissionErrors.length > 0"
                        class="red"
                    >
                        <div
                            v-for="(err, index) in state.submissionErrors"
                            :key="index"
                            class="red"
                        >
                            <strong>{{ err.error }}:</strong>
                            {{ err.message }}
                        </div>
                    </div>
                    <StepPanels class="bc-step-card">
                        <StepPanel
                            v-for="(step, i) in steps"
                            :key="i"
                            :value="i + 1"
                        >
                            <h3
                                v-if="headingFor(step)"
                                class="heading-margin-bottom"
                            >
                                {{ headingFor(step) }}
                            </h3>
                            <component
                                :is="step.component"
                                :ref="(el: unknown) => setStepRef(i, el)"
                                @update:step-is-valid="
                                    setCurrentStepValid($event, i + 1)
                                "
                            ></component>
                        </StepPanel>
                        <StepPanel :value="reviewStepNumber">
                            <h3 class="heading-margin-bottom">
                                Review Submission
                            </h3>
                            <component
                                :is="reviewComponent"
                                :ref="
                                    (el: unknown) =>
                                        setStepRef(reviewStepNumber - 1, el)
                                "
                                @update:step-is-valid="
                                    setCurrentStepValid(
                                        $event,
                                        reviewStepNumber,
                                    )
                                "
                            ></component>
                        </StepPanel>
                        <StepPanel :value="totalSteps">
                            <h3 class="heading-margin-bottom">Submitted</h3>
                            <component
                                :is="reviewComponent"
                                :ref="
                                    (el: unknown) =>
                                        setStepRef(totalSteps - 1, el)
                                "
                                :is-submitted-view="true"
                                :resource-data="finalizedDataForReview"
                                @update:step-is-valid="
                                    setCurrentStepValid($event, totalSteps)
                                "
                            ></component>
                            <RouterLink
                                v-if="permitBackLink"
                                :to="permitBackLink"
                                class="back-to-permit mt-4"
                            >
                                <i class="fa-solid fa-chevron-left"></i>
                                Back to Filing Summary
                            </RouterLink>
                        </StepPanel>
                        <div class="bc-step-actions">
                            <StepperNavigation
                                :step-number="currentStep"
                                :is-valid="currentStepIsValid"
                                :show-previous="showPrevious"
                                :next-label="nextLabel"
                                @next-click="activateNextStep"
                                @previous-click="activatePreviousStep"
                            ></StepperNavigation>
                        </div>
                    </StepPanels>
                </div>
            </div>
        </Stepper>
    </Panel>
    <br />
    <br />
    <br />
</template>

<style>
@import url('@/bcgov_arches_common/css/arches_common.css');
@import url('@/bcap/styles/bc-stepper.css');
.language-selector {
    display: none;
}
/* The shared nav is laid out by .bc-step-actions now; just drop the empty
   spacer it inserts when Previous is hidden. */
.stepper-nav-panel {
    display: flex;
    align-items: center;
    gap: 1rem;
}
.stepper-nav-panel > div {
    display: none;
}
@media print {
    aside,
    .bc-stepper-nav,
    .stepper-nav-panel,
    .sidenav {
        display: none !important;
    }
}
.red {
    color: red;
}
.back-to-permit {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    /* Same fixed line box as the rail's "Your progress" label so the two center
       on the same line on step 1, where this is the header's first line. */
    min-height: 1.75rem;
    margin-bottom: 1rem;
    line-height: 1;
    color: var(--bc-navy, #003366);
    font-weight: 700;
    text-decoration: none;
}
.back-to-permit .fa-chevron-left {
    font-size: 0.85em;
    line-height: 1;
    position: relative;
    top: 1px;
}
.back-to-permit:hover {
    color: #1a5a96;
    text-decoration: none;
}
</style>
<style scoped>
.submit-overlay {
    display: flex;
    justify-content: center;
    align-items: center;
    opacity: 0.7;
    position: absolute;
    width: 100vw;
    height: 100vh;
    background: white;
    z-index: 500;
    left: 0;
    top: 0;
}
</style>
