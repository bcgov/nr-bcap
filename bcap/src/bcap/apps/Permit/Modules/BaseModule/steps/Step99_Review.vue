<script setup lang="ts">
import { inject, computed, type Ref } from 'vue';
import FieldSet from 'primevue/fieldset';
import GenericReviewSummary, {
    type ReviewField,
} from '@/bcap/apps/Permit/Modules/ReviewSummary.vue';
import { getBasicInfoFields, type PermitAliasedData } from '@/bcap/util.ts';
import type { ArchesDraftData } from '@/bcap/types.ts';

const props = defineProps<{
    isSubmittedView?: boolean;
    resourceData?: ArchesDraftData | null;
}>();

const draftData = inject<Ref<ArchesDraftData>>('draftData');

const activeData = computed<ArchesDraftData>(() => {
    if (props.isSubmittedView && props.resourceData) return props.resourceData;
    return draftData?.value || ({} as ArchesDraftData);
});

const basicInfoFields = computed<ReviewField[]>(() => {
    return getBasicInfoFields(activeData.value as unknown as PermitAliasedData);
});

const isValid = () => true;
defineExpose({ isValid });
</script>

<template>
    <p
        v-if="!isSubmittedView"
        class="mb-4"
    >
        Please review the entered information prior to submitting the
        application:
    </p>
    <div
        v-else
        class="mb-4"
    >
        <p>
            Your application has been successfully submitted. Below is a summary
            of the finalized information.
        </p>
    </div>

    <FieldSet class="review-fieldset">
        <GenericReviewSummary :fields="basicInfoFields" />
    </FieldSet>
</template>
