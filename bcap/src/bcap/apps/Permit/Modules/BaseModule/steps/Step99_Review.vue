<script setup lang="ts">
import Step99_Review from '@/bcap/apps/Permit/Modules/Step99_Review.vue';
import GenericReviewSummary from '@/bcap/apps/Permit/Modules/ReviewSummary.vue';
import { getBasicInfoFields } from '@/bcap/util.ts';
import type { ArchesDraftData, PermitAliasedData } from '@/bcap/types.ts';

defineProps<{
    isSubmittedView?: boolean;
    resourceData?: ArchesDraftData | null;
}>();

const fields = (data: ArchesDraftData) =>
    getBasicInfoFields(data as unknown as PermitAliasedData);

const isValid = () => true;
defineExpose({ isValid });
</script>

<template>
    <Step99_Review
        :is-submitted-view="isSubmittedView"
        :resource-data="resourceData"
    >
        <template #default="{ data }">
            <GenericReviewSummary :fields="fields(data)" />
        </template>
    </Step99_Review>
</template>
