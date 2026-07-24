<script setup lang="ts">
import WorkflowStepper from '@/bcap/apps/Permit/Modules/WorkflowStepper.vue';
import { GraphSlug } from '@/bcap/apps/Permit/graphSlug.ts';
import Step1_About from '@/bcap/apps/Permit/Modules/InvestigationModule/steps/Step1_About.vue';
import Step2_Overview from '@/bcap/apps/Permit/Modules/InvestigationModule/steps/Step2_Overview.vue';
import Step3_Personnel from '@/bcap/apps/Permit/Modules/InvestigationModule/steps/Step3_Personnel.vue';
import Step4_Methods from '@/bcap/apps/Permit/Modules/InvestigationModule/steps/Step4_Methods.vue';
import Step5_Recordings from '@/bcap/apps/Permit/Modules/InvestigationModule/steps/Step5_Recordings.vue';
import Step6_Materials from '@/bcap/apps/Permit/Modules/InvestigationModule/steps/Step6_Materials.vue';
import Step7_Remains from '@/bcap/apps/Permit/Modules/InvestigationModule/steps/Step7_Remains.vue';
import Step8_Repository from '@/bcap/apps/Permit/Modules/InvestigationModule/steps/Step8_Repository.vue';

const steps = [
    { label: 'Submission Information', component: Step1_About, heading: '' },
    { label: 'Preamble', component: Step2_Overview },
    { label: 'Personnel', component: Step3_Personnel },
    { label: 'Methods', component: Step4_Methods },
    { label: 'Recordings and Site Evaluation', component: Step5_Recordings },
    { label: 'Collection of Materials', component: Step6_Materials },
    { label: 'Ancestral Remains', component: Step7_Remains },
    { label: 'Repositories and Curation', component: Step8_Repository },
];
</script>

<template>
    <WorkflowStepper
        :graph-slug="GraphSlug.Investigation"
        title="Submit Investigation"
        :steps="steps"
    />
</template>
