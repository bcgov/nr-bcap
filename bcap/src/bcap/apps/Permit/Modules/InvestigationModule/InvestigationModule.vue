<script setup lang="ts">
import { computed, reactive, ref, onMounted } from 'vue';
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
import type { Ref } from 'vue';
import type { StepperProps, StepperState } from 'primevue/stepper';

import Step1_About from '@/bcap/apps/Permit/Modules/InvestigationModule/steps/Step1_About.vue';
import Step2_Overview from '@/bcap/apps/Permit/Modules/InvestigationModule/steps/Step2_Overview.vue';
import Step3_Personnel from '@/bcap/apps/Permit/Modules/InvestigationModule/steps/Step3_Personnel.vue';
import Step4_Methods from '@/bcap/apps/Permit/Modules/InvestigationModule/steps/Step4_Methods.vue';
import Step5_Recordings from '@/bcap/apps/Permit/Modules/InvestigationModule/steps/Step5_Recordings.vue';
import Step6_Materials from '@/bcap/apps/Permit/Modules/InvestigationModule/steps/Step6_Materials.vue';
import Step7_Remains from '@/bcap/apps/Permit/Modules/InvestigationModule/steps/Step7_Remains.vue';
import Step8_Repository from '@/bcap/apps/Permit/Modules/InvestigationModule/steps/Step8_Repository.vue';
import Step99_Review from '@/bcap/apps/Permit/Modules/InvestigationModule/steps/Step99_Review.vue';
import type { ErrorMessage } from '@/bcgov_arches_common/types.ts';
import type { ArchesDraftData } from '@/bcap/types.ts';
import { submitModule, fetchDraft } from '@/bcap/apps/Permit/api.ts';
import type { PermitApplicationResponse } from '@/bcap/types.ts';
import { routeNames } from '@/bcap/apps/Permit/routes.ts';
import { GraphSlug } from '@/bcap/apps/Permit/graphSlug.ts';

const graphSlug = GraphSlug.Investigation;
const route = useRoute();

const draft = useDraftStore();
// The permit this investigation was started from. From the URL when starting
// fresh, or the loaded draft's parent_resource_id when resuming.
draft.initDraft(graphSlug, (route.query.permitId as string) ?? null);

const state = reactive({
    submissionErrors: [] as ErrorMessage[],
    submitted: false,
    submitting: false,
    devMode: true,
    isDataLoaded: false,
    finalizedResourceData: null as PermitApplicationResponse | null,
});

const permitBackLink = computed(() =>
    draft.parentPermitId
        ? {
              name: routeNames.permitDetails,
              params: { id: draft.parentPermitId },
          }
        : null,
);

const finalizedDataForReview = computed<ArchesDraftData | null>(() => {
    if (!state.finalizedResourceData?.aliased_data) return null;
    return state.finalizedResourceData
        .aliased_data as unknown as ArchesDraftData;
});

const submitNewSiteData = async (): Promise<boolean> => {
    state.submitting = true;
    state.submissionErrors = [];

    try {
        if (!draft.draftId) throw new Error('No active draft found.');
        if (!draft.parentPermitId)
            throw new Error('No permit associated with this investigation.');

        const response = await submitModule(
            draft.parentPermitId,
            draft.draftId,
            GraphSlug.Investigation,
            draft.draftData,
        );

        if (response) {
            state.finalizedResourceData = response;
        }

        return true;
    } catch (error) {
        console.error('Submission failed:', error);
        const errorMessage =
            error instanceof Error
                ? error.message
                : 'An unknown error occurred.';

        state.submissionErrors.push({
            type: 'Submission Error',
            error: 'Submission Failed',
            message: errorMessage,
        });
        return false;
    } finally {
        state.submitting = false;
    }
};

const print = () => {
    window.print();
};

const activateNextStep = async () => {
    if (currentStep.value === steps.length) {
        print();
    } else if (currentStep.value === steps.length - 1) {
        const success = await submitNewSiteData();

        if (success) {
            myStepper.value.d_value++;
            setCurrentStepValid(true, myStepper.value.d_value);
        }
    } else {
        myStepper.value.d_value++;
        setCurrentStepValid(
            steps[myStepper.value.d_value - 1].value.isValid(),
            myStepper.value.d_value,
        );
    }
};

const activatePreviousStep = () => {
    setCurrentStepValid(
        steps[myStepper.value.d_value - 2].value.isValid(),
        myStepper.value.d_value - 1,
    );
    myStepper.value.d_value--;
};

function activateStep(step: number) {
    if (step > lastStep && !isValid(lastStep)) {
        myStepper.value.d_value = lastStep;
    } else {
        lastStep = step;
        setCurrentStepValid(steps[step - 1].value.isValid(), step);
    }
}

const stepStatuses: Ref<boolean[]> = ref([]);

const currentStepIsValid = computed(() => {
    return stepStatuses.value[currentStep.value - 1];
});

const setCurrentStepValid = function (isValid: boolean, stepNumber: number) {
    stepStatuses.value[stepNumber - 1] = isValid;
};

const isValid = (step: number) => {
    if (state.devMode) return true;
    let stepValid = true;

    if (typeof steps[step - 1]?.value?.isValid === 'function') {
        stepValid = steps[step - 1]?.value?.isValid();
    }
    if (step === steps.length) {
        state.submitted = true;
    }

    return stepValid;
};

const stepperProps: Ref<StepperProps | null> = ref(null);
const stepperState: Ref<StepperState | null> = ref(null);
const myStepper = ref();
const step1 = ref();
const step2 = ref();
const step3 = ref();
const step4 = ref();
const step5 = ref();
const step6 = ref();
const step7 = ref();
const step8 = ref();
const step9 = ref();
const step10 = ref();
const steps: Ref[] = [];
let lastStep = 1;

const currentStep = computed(() => {
    return myStepper.value?.d_value;
});

onMounted(async () => {
    steps.push(
        step1,
        step2,
        step3,
        step4,
        step5,
        step6,
        step7,
        step8,
        step9,
        step10,
    );

    try {
        // Only load an existing draft. A new one isn't created until the first
        // edit (store.ensureDraftId), so an abandoned form leaves no empty draft.
        // parentPermitId for a fresh draft already came from the URL via initDraft.
        const targetDraftId = route.query.draftId;
        if (targetDraftId) {
            const loaded = await fetchDraft(graphSlug, targetDraftId as string);
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

const nextLabel = computed(() => {
    if (currentStep.value === steps.length) return 'Print';
    return currentStep.value < steps.length - 1 ? 'Next' : 'Create Application';
});

const showPrevious = computed(() => {
    return !(currentStep.value === steps.length || currentStep.value === 1);
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
                        <Step :value="1">Submission Information</Step>
                        <Step :value="2">Preamble</Step>
                        <Step :value="3">Personnel</Step>
                        <Step :value="4">Methods</Step>
                        <Step :value="5">Recordings and Site Evaluation</Step>
                        <Step :value="6">Collection of Materials</Step>
                        <Step :value="7">Ancestral Remains</Step>
                        <Step :value="8">Repositories and Curation</Step>
                        <Step :value="9">Review Submission</Step>
                        <Step :value="10">Submission Complete</Step>
                    </StepList>
                </aside>
                <div class="bc-stepper-main">
                    <RouterLink
                        v-if="permitBackLink && currentStep === 1"
                        :to="permitBackLink"
                        class="back-to-permit"
                    >
                        <i class="fa-solid fa-chevron-left"></i>
                        Back to permit
                    </RouterLink>
                    <header class="bc-step-header">
                        <div>
                            <p class="bc-step-eyebrow">
                                Step {{ currentStep }} of {{ steps.length }}
                            </p>
                            <h1 class="bc-step-title">Submit Investigation</h1>
                        </div>
                        <StepperNavigation
                            :step-number="currentStep"
                            :is-valid="currentStepIsValid"
                            :show-previous="showPrevious"
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
                        <StepPanel :value="1">
                            <Step1_About ref="step1"></Step1_About>
                        </StepPanel>
                        <StepPanel :value="2">
                            <h3 class="heading-margin-bottom">Preamble</h3>
                            <Step2_Overview
                                ref="step2"
                                @update:step-is-valid="
                                    setCurrentStepValid($event, 2)
                                "
                            ></Step2_Overview>
                        </StepPanel>
                        <StepPanel :value="3">
                            <h3 class="heading-margin-bottom">Personnel</h3>
                            <Step3_Personnel
                                ref="step3"
                                @update:step-is-valid="
                                    setCurrentStepValid($event, 3)
                                "
                            ></Step3_Personnel>
                        </StepPanel>
                        <StepPanel :value="4">
                            <h3 class="heading-margin-bottom">Methods</h3>
                            <Step4_Methods
                                ref="step4"
                                @update:step-is-valid="
                                    setCurrentStepValid($event, 4)
                                "
                            ></Step4_Methods>
                        </StepPanel>
                        <StepPanel :value="5">
                            <h3 class="heading-margin-bottom">
                                Recordings and Site Evaluation
                            </h3>
                            <Step5_Recordings
                                ref="step5"
                                @update:step-is-valid="
                                    setCurrentStepValid($event, 5)
                                "
                            ></Step5_Recordings>
                        </StepPanel>
                        <StepPanel :value="6">
                            <h3 class="heading-margin-bottom">
                                Collection of Materials
                            </h3>
                            <Step6_Materials
                                ref="step6"
                                @update:step-is-valid="
                                    setCurrentStepValid($event, 6)
                                "
                            ></Step6_Materials>
                        </StepPanel>
                        <StepPanel :value="7">
                            <h3 class="heading-margin-bottom">
                                Ancestral Remains
                            </h3>
                            <Step7_Remains
                                ref="step7"
                                @update:step-is-valid="
                                    setCurrentStepValid($event, 7)
                                "
                            ></Step7_Remains>
                        </StepPanel>
                        <StepPanel :value="8">
                            <h3 class="heading-margin-bottom">
                                Repositories and Curation
                            </h3>
                            <Step8_Repository
                                ref="step8"
                                @update:step-is-valid="
                                    setCurrentStepValid($event, 8)
                                "
                            ></Step8_Repository>
                        </StepPanel>
                        <StepPanel :value="9">
                            <h3 class="heading-margin-bottom">
                                Review Submission
                            </h3>
                            <Step99_Review
                                ref="step9"
                                @update:step-is-valid="
                                    setCurrentStepValid($event, 9)
                                "
                            ></Step99_Review>
                        </StepPanel>
                        <StepPanel :value="10">
                            <h3 class="heading-margin-bottom">Submitted</h3>
                            <Step99_Review
                                ref="step10"
                                :is-submitted-view="true"
                                :resource-data="finalizedDataForReview"
                                @update:step-is-valid="
                                    setCurrentStepValid($event, 10)
                                "
                            ></Step99_Review>
                            <RouterLink
                                v-if="permitBackLink"
                                :to="permitBackLink"
                                class="back-to-permit mt-4"
                            >
                                <i class="fa-solid fa-chevron-left"></i>
                                Back to permit application
                            </RouterLink>
                        </StepPanel>
                    </StepPanels>
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
