<script setup lang="ts">
import { computed } from 'vue';
import FieldSet from 'primevue/fieldset';
import GenericReviewSummary, {
    type ReviewField,
} from '@/bcap/apps/Permit/Modules/ReviewSummary.vue';
import { useDraftStore } from '@/bcap/stores/draft.ts';
import type { ArchesDraftData, DraftNode } from '@/bcap/types.ts';

const props = defineProps<{
    isSubmittedView?: boolean;
    resourceData?: ArchesDraftData | null;
}>();

const draft = useDraftStore();

const activeData = computed<ArchesDraftData>(() =>
    props.isSubmittedView && props.resourceData
        ? props.resourceData
        : (draft.draftData as ArchesDraftData) || ({} as ArchesDraftData),
);

const humanize = (alias: string) =>
    alias.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

// Walk every section's nodes (and nested node groups) into review fields.
// GenericReviewSummary hides the empty ones, so no per-node curation needed.
const walk = (
    nodes: Record<string, DraftNode | null> | undefined,
    fields: ReviewField[],
) => {
    if (!nodes) return;
    for (const [alias, node] of Object.entries(nodes)) {
        if (!node) continue;
        if (node.aliased_data) {
            walk(node.aliased_data, fields);
        } else {
            fields.push({ label: humanize(alias), value: node.display_value });
        }
    }
};

const reviewFields = computed<ReviewField[]>(() => {
    const fields: ReviewField[] = [];
    for (const section of Object.values(activeData.value)) {
        walk(section?.aliased_data, fields);
    }
    return fields;
});

const isValid = () => true;
defineExpose({ isValid });
</script>

<template>
    <p class="review-intro">
        {{
            isSubmittedView
                ? 'Your application has been successfully submitted. Below is a summary of the finalized information.'
                : 'Please review the entered information prior to submitting the application:'
        }}
    </p>

    <FieldSet class="review-fieldset">
        <!-- Default: generic summary of every filled node. Override the slot to
             curate fields (the permit application does). -->
        <slot
            :data="activeData"
            :fields="reviewFields"
        >
            <GenericReviewSummary :fields="reviewFields" />
        </slot>
    </FieldSet>
</template>

<style scoped>
.review-intro {
    margin-bottom: 1.5rem;
}
.review-fieldset {
    margin-bottom: 2rem;
}
.review-fieldset :deep(.p-fieldset-content) {
    padding: 1.5rem;
}
</style>
