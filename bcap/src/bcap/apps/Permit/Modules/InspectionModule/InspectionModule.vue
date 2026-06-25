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
import { getCsrfToken } from '@/bcap/util.ts';

import Step1_About from '@/bcap/apps/Permit/Modules/InspectionModule/steps/Step1_About.vue';
import Step2_Prelim from '@/bcap/apps/Permit/Modules/InspectionModule/steps/Step2_Prelim.vue';
import Step99_Review from '@/bcap/apps/Permit/Modules/InspectionModule/steps/Step99_Review.vue';
import type { ErrorMessage } from '@/bcgov_arches_common/types.ts';
import type { ArchesDraftData, DraftNode } from '@/bcap/types.ts';
import { submitApplication } from '@/bcap/apps/Permit/api.ts';
import type { PermitApplicationResponse } from '@/bcap/apps/Permit/api.ts';

const submissionErrors = ref([] as ErrorMessage[]);
const submitted = ref(false);
const submitting = ref(false);
const devMode = ref(true);
const isDataLoaded = ref(false);
const graphSlug = 'inspection';
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
    console.log('Submitting final application...');
    submitting.value = true;
    submissionErrors.value = [];

    try {
        if (!draftId.value) throw new Error('No active draft found.');

        // Stamp the submission date: this is the actual submission, and the
        // server treats application_submission_date as the "submitted" signal.
        // This is temp to get UAT going.
        draftData.value.application_admin = {
            ...draftData.value.application_admin,
            aliased_data: {
                ...draftData.value.application_admin?.aliased_data,
                application_submission_date: {
                    node_value: new Date().toISOString().slice(0, 10),
                } as DraftNode,
            },
        };

        // Submit the draft
        const response = await submitApplication(
            draftId.value,
            draftData.value,
            graphSlug,
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
            console.log(
                'Submission successful. Moving to confirmation step...',
            );
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
const step1 = ref(); // About
const step2 = ref(); // Prelim
const step3 = ref(); // Review
const step4 = ref(); // Submitted
const steps: Ref[] = [];
let lastStep = 1;

const currentStep = computed(() => {
    return myStepper.value?.d_value;
});

onMounted(async () => {
    steps.push(step1, step2, step3, step4);

    try {
        //Check if the URL has a draftId
        const targetDraftId = route.query.draftId;

        if (targetDraftId) {
            console.log(`Resuming specific draft: ${targetDraftId}`);

            const response = await fetch(
                `/bcap/api/resource_draft/${graphSlug}/${targetDraftId}`,
            );

            if (!response.ok)
                throw new Error(`Failed to fetch draft ${targetDraftId}`);

            const draft = await response.json();
            draftId.value = draft.id;
            draftData.value = draft.data || {};
        } else {
            console.log('No draftId in URL, creating a brand new draft...');

            const createResponse = await fetch(
                `/bcap/api/resource_draft/${graphSlug}`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken(),
                    },
                    body: JSON.stringify({ data: {} }),
                },
            );

            if (!createResponse.ok)
                throw new Error(
                    `Failed to create draft. Status: ${createResponse.status}`,
                );

            const newDraft = await createResponse.json();
            draftId.value = newDraft.id;
            draftData.value = {};
        }

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
        id="debug-div"
        v-show="showDebug"
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
                        <Step :value="3">Review Submission</Step>
                        <Step :value="4">Submission Complete</Step>
                    </StepList>
                </div>
                <div class="bcgov-vertical-step-panels">
                    <h1>Submit Permit Application</h1>
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
                            <Step2_Prelim
                                ref="step2"
                                @update:step-is-valid="
                                    setCurrentStepValid($event, 2)
                                "
                            ></Step2_Prelim>
                        </StepPanel>

                        <StepPanel :value="3">
                            <h3 class="heading-margin-bottom">
                                Review Submission
                            </h3>
                            <Step99_Review
                                ref="step3"
                                @update:step-is-valid="
                                    setCurrentStepValid($event, 3)
                                "
                            ></Step99_Review>
                        </StepPanel>

                        <StepPanel :value="4">
                            <h3 class="heading-margin-bottom">Submitted</h3>
                            <Step99_Review
                                ref="step4"
                                :is-submitted-view="true"
                                :resource-data="finalizedDataForReview"
                                @update:step-is-valid="
                                    setCurrentStepValid($event, 4)
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
