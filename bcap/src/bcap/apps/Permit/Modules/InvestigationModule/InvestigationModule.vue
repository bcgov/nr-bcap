<script setup lang="ts">
import { computed, ref, provide, onMounted } from 'vue';
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
import {
    submitInvestigation,
    fetchDraft,
    createDraft,
} from '@/bcap/apps/Permit/api.ts';
import type { PermitApplicationResponse } from '@/bcap/apps/Permit/api.ts';

const submissionErrors = ref([] as ErrorMessage[]);
const submitted = ref(false);
const submitting = ref(false);
const devMode = ref(true);
const isDataLoaded = ref(false);
const graphSlug = 'investigation';
const draftId = ref<string | null>(null);
const draftData = ref<ArchesDraftData>({});
const finalizedResourceData = ref<PermitApplicationResponse | null>(null);
const route = useRoute();

provide('draftId', draftId);
provide('draftData', draftData);

const finalizedDataForReview = computed<ArchesDraftData | null>(() => {
    if (!finalizedResourceData.value?.aliased_data) return null;
    return finalizedResourceData.value
        .aliased_data as unknown as ArchesDraftData;
});

const submitNewSiteData = async (): Promise<boolean> => {
    submitting.value = true;
    submissionErrors.value = [];

    try {
        if (!draftId.value) throw new Error('No active draft found.');

        const response = await submitInvestigation(
            draftId.value,
            draftData.value,
        );

        if (response) {
            finalizedResourceData.value = response;
        }

        return true;
    } catch (error) {
        console.error('Submission failed:', error);
        const errorMessage =
            error instanceof Error
                ? error.message
                : 'An unknown error occurred.';

        submissionErrors.value.push({
            type: 'Submission Error',
            error: 'Submission Failed',
            message: errorMessage,
        });
        return false;
    } finally {
        submitting.value = false;
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
    if (devMode.value) return true;
    let stepValid = true;

    if (typeof steps[step - 1]?.value?.isValid === 'function') {
        stepValid = steps[step - 1]?.value?.isValid();
    }
    if (step === steps.length) {
        submitted.value = true;
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
        const targetDraftId = route.query.draftId;
        const draft = targetDraftId
            ? await fetchDraft(graphSlug, targetDraftId as string)
            : await createDraft(graphSlug);
        draftId.value = draft.id;
        draftData.value = draft.data || {};

        isDataLoaded.value = true;
    } catch (error) {
        console.error('Failed to initialize draft:', error);
        isDataLoaded.value = true;
    }
});

const nextLabel = computed(() => {
    if (currentStep.value === steps.length) return 'Print';
    return currentStep.value < steps.length - 1 ? 'Next' : 'Create Application';
});

const showPrevious = computed(() => {
    return !(currentStep.value === steps.length || currentStep.value === 1);
});
const showDebug = ref(false);
</script>

<template>
    <div
        v-if="submitting"
        class="submit-overlay"
    >
        <ProgressSpinner />
    </div>
    <div
        v-show="showDebug"
        id="debug-div"
        class="debug-step"
        :class="{ 'show-debug': showDebug }"
    >
        {{ JSON.stringify('') }}
    </div>
    <i
        class="fa fa-eye-slash debug-toggle"
        @click="showDebug = !showDebug"
    ></i>
    <Panel class="full-height">
        <div
            v-if="!isDataLoaded"
            style="display: flex; justify-content: center; padding: 3rem"
        >
            <ProgressSpinner />
        </div>

        <Stepper
            v-if="isDataLoaded"
            ref="myStepper"
            :state="stepperState"
            :props="stepperProps"
            :value="1"
            linear
            @update:value="activateStep"
        >
            <div class="bcgov-stepper">
                <div class="bcgov-vertical-steps">
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
                </div>
                <div class="bcgov-vertical-step-panels">
                    <h1>Submit Investigation</h1>
                    <div
                        v-if="submissionErrors.length > 0"
                        class="red"
                    >
                        <div
                            v-for="(err, index) in submissionErrors"
                            :key="index"
                            class="red"
                        >
                            <strong>{{ err.error }}:</strong>
                            {{ err.message }}
                        </div>
                    </div>
                    <StepPanels>
                        <StepperNavigation
                            :step-number="currentStep"
                            :is-valid="currentStepIsValid"
                            :show-previous="showPrevious"
                            :next-label="nextLabel"
                            @next-click="activateNextStep"
                            @previous-click="activatePreviousStep"
                        ></StepperNavigation>
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
                        </StepPanel>
                        <StepperNavigation
                            :step-number="currentStep"
                            :is-valid="currentStepIsValid"
                            :show-previous="showPrevious"
                            :next-label="nextLabel"
                            @next-click="activateNextStep"
                            @previous-click="activatePreviousStep"
                        ></StepperNavigation>
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
.language-selector {
    display: none;
}
/* The shared nav drops an empty block spacer in when Previous is hidden, which
   pushes Next onto its own line. Hiding it keeps Next on the button row. */
.stepper-nav-panel > div {
    display: none;
}
@media print {
    aside,
    .bcgov-vertical-steps,
    .stepper-nav-panel,
    .sidenav,
    .debug-toggle {
        display: none !important;
    }
}
.red {
    color: red;
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
.debug-step {
    max-width: 80%;
    margin-top: 100px;
    display: none;
    position: absolute;
    bottom: 10px;
    word-wrap: anywhere;
    color: darkgray;
}
.show-debug {
    display: inline-block !important;
}
.debug-toggle {
    position: absolute;
    top: 0;
    left: 0.5rem;
    color: white;
    z-index: 9000;
}
</style>
