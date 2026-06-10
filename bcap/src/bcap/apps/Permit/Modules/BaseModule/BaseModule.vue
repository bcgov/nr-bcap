<script setup lang="ts">
import { computed, ref, /*provide,*/ onMounted } from 'vue';
import Stepper from 'primevue/stepper';
import Step from 'primevue/step';
import StepPanel from 'primevue/steppanel';
import StepList from 'primevue/steplist';
import StepPanels from 'primevue/steppanels';
import ProgressSpinner from 'primevue/progressspinner';
import StepperNavigation from '@/bcgov_arches_common/components/Stepper/components/StepperNavigation/StepperNavigation.vue';

import Panel from 'primevue/panel';

import type { Ref } from 'vue';
import type { StepperProps } from 'primevue/stepper';
import type { StepperState } from 'primevue/stepper';

import Step1_About from '@/bcap/apps/Permit/Modules/BaseModule/steps/Step1_About.vue';
import Step2_Prelim from '@/bcap/apps/Permit/Modules/BaseModule/steps/Step2_Prelim.vue';
import Step3_Details1 from '@/bcap/apps/Permit/Modules/BaseModule/steps/Step3_Details.vue';
import Step99_Review from '@/bcap/apps/Permit/Modules/BaseModule/steps/Step99_Review.vue';
import type { ErrorMessage } from '@/bcgov_arches_common/types.ts';

const submissionErrors = ref([] as ErrorMessage[]);
const submitted = ref(false);
const submitting = ref(false);
const devMode = ref(true);
const isDataLoaded = ref(false);

//placeholder function for final submission
// const submitNewSiteData = async () => {
//     console.log('submit Heritage Site', heritageSite);
//     submitting.value = true;
//     submissionErrors.value = [];
//     submitHeritageSite(heritageSite.value)
//         .then((updatedHeritageSite) => {
//             heritageSite.value =
//                 updatedHeritageSite as Promise<HeritageSiteType>;
//             myStepper.value.d_value++;
//             // Didn't throw an exception so the last step is valid.
//             setCurrentStepValid(true, myStepper.value.d_value);
//             submissionErrors.value = [];
//             submitting.value = false;
//         })
//         .catch((error) => {
//             console.log('raw error', error);
//             submissionErrors.value = parseBackendError(error);
//             submitting.value = false;
//         });
// };

// const parseBackendError = (backendError: any): ErrorMessage[] => {
//     const payload = backendError?.response?.data || backendError;
//     const type = payload?.type || 'Validation Error';
//     const messageStr = payload?.message || '';
//     const errorMatches = [
//         ...messageStr.matchAll(
//             /'([^']+)'\s*:\s*\[ErrorDetail\(string=".*?\s*-\s*(.*?)",/g,
//         ),
//     ];
//
//     if (errorMatches.length > 0) {
//         return errorMatches.map((match) => ({
//             type: type,
//             error: match[1].replace('_', ' ').toUpperCase(),
//             message: match[2],
//         }));
//     }
//
//     return [
//         {
//             type: type,
//             error: payload?.error || 'Submission Failed',
//             message:
//                 typeof messageStr === 'string'
//                     ? messageStr
//                     : 'Please review your inputs.',
//         },
//     ];
// };

const print = () => {
    window.print();
};

const activateNextStep = async () => {
    if (currentStep.value === steps.length) {
        print();
        // } else if (currentStep.value === 11) {
        //     submitNewSiteData();
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

// const printDetails = () => {
//     console.log('printDetails');
// };

const stepperProps: Ref<StepperProps | null> = ref(null);
const stepperState: Ref<StepperState | null> = ref(null);
const myStepper = ref();
const step1 = ref();
const step2 = ref();
const step3 = ref();
const step99 = ref();
const steps: Ref[] = [];
let lastStep = 1;
const currentStep = computed(() => {
    return myStepper.value?.d_value;
});
// const heritageSite: Ref<HeritageSiteType> = ref(getHeritageSite());

// provide('heritageSite', heritageSite);

onMounted(() => {
    console.log(submissionErrors);
    steps.push(step1, step2, step3, step99);

    // if (siteId) {
    //     getHeritageSiteById(siteId).then((existingData) => {
    //         heritageSite.value = existingData as unknown as HeritageSiteType;
    //
    //         isDataLoaded.value = true;
    //         console.log('existing data object', heritageSite.value);
    //     });
    // } else {
    // getBlankHeritageSite().then((response) => {
    //     heritageSite.value = response as unknown as HeritageSiteType;
    //     isDataLoaded.value = true;
    // });
    // }
    isDataLoaded.value = true;
});

const nextLabel = computed(() => {
    if (currentStep.value === steps.length) return 'Print';
    return currentStep.value < steps.length - 1 ? 'Next' : 'Submit';
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
        id="debug-div"
        :v-show="showDebug"
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
                        <Step :value="3">Details</Step>
                        <Step :value="4">Review Submission</Step>
                        <Step :value="5">Submission Complete</Step>
                    </StepList>
                </div>
                <div class="bcgov-vertical-step-panels">
                    <h1>Submit Permit Application</h1>
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
                            <Step2_Prelim
                                ref="step2"
                                @update:step-is-valid="
                                    setCurrentStepValid($event, 2)
                                "
                            ></Step2_Prelim>
                        </StepPanel>
                        <StepPanel :value="3">
                            <h3 class="heading-margin-bottom">
                                Project Details
                            </h3>
                            <Step3_Details1
                                ref="step3"
                                @update:step-is-valid="
                                    setCurrentStepValid($event, 3)
                                "
                            ></Step3_Details1>
                        </StepPanel>

                        <StepPanel :value="4">
                            <h3 class="heading-margin-bottom">
                                Review Submission
                            </h3>
                            <Step99_Review
                                ref="step15"
                                @update:step-is-valid="
                                    setCurrentStepValid($event, 15)
                                "
                            ></Step99_Review>
                        </StepPanel>
                        <StepPanel :value="5">
                            <h3 class="heading-margin-bottom">Submitted</h3>
                            <Step99_Review
                                ref="step99"
                                @update:step-is-valid="
                                    setCurrentStepValid($event, 16)
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
@media print {
    aside,
    .bcgov-vertical-steps,
    .stepper-nav-panel,
    .sidenav,
    .debug-toggle {
        display: none !important;
    }

    html,
    body {
        height: auto !important;
        overflow: visible !important;
    }

    .main-content-area,
    .page-wrapper,
    main {
        position: static !important;
        overflow: visible !important;
        height: auto !important;
        width: 100% !important;
        max-width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        display: block !important;
    }

    .bcgov-stepper,
    .bcgov-vertical-step-panels {
        display: block !important;
        width: 100% !important;
        max-width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        flex: none !important;
    }

    .p-panel,
    .p-panel-content,
    .p-panel-header {
        padding-top: 0 !important;
        margin-top: 0 !important;
        border: none !important;
    }

    .bcgov-vertical-step-panels h1 {
        margin-top: 0 !important;
        padding-top: 0 !important;
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
.dashboard-card {
    font-size: 1.1rem;
    margin: 1rem;
    max-width: 33%;
}

.p-card-content {
    font-size: 1rem;
}

li {
    color: var(--p-primary-color);
}

.step-title {
    margin-bottom: 1rem;
    font-size: 21px;
    font-weight: bold;
    line-height: inherit;
    color: #333;
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
