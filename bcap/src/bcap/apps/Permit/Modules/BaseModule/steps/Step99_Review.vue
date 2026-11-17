<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import Step99_Review from '@/bcap/apps/Permit/Modules/Step99_Review.vue';
import GenericReviewSummary from '@/bcap/apps/Permit/Modules/ReviewSummary.vue';
import type { ReviewField } from '@/bcap/apps/Permit/Modules/ReviewSummary.vue';
import type { ArchesDraftData } from '@/bcap/types.ts';
import type { BcapServiceRequestResourceAliasedData } from '@/bcap/client/types.gen.ts';
import { useDraftStore } from '@/bcap/stores/draft.ts';
import {
    fetchWfsIntersect,
    type CrownTenureFeature,
} from '@/bcap/apps/Permit/api.ts';
import { getServiceRequestInfoFields } from '@/bcap/util.ts';

const CROWN_TENURES_LAYER = 'WHSE_TANTALIS.TA_CROWN_TENURES_SVW';

const props = defineProps<{
    isSubmittedView?: boolean;
    resourceData?: ArchesDraftData | null;
}>();

const draft = useDraftStore();

// Mirror the same active-data logic as the generic Step99_Review so we can
// watch the boundary regardless of whether we're in the workflow or review.
const activeSrData = computed<BcapServiceRequestResourceAliasedData>(() => {
    const data =
        props.isSubmittedView && props.resourceData
            ? props.resourceData
            : (draft.draftData as ArchesDraftData);
    return (data as unknown as BcapServiceRequestResourceAliasedData) ?? {};
});

const tenures = ref<CrownTenureFeature[]>([]);

watch(
    () =>
        activeSrData.value?.service_request_location?.aliased_data
            ?.service_request_boundary?.node_value,
    async (boundary) => {
        const hasFeatures =
            boundary &&
            (boundary.type !== 'FeatureCollection' ||
                (boundary.features?.length ?? 0) > 0);
        if (!hasFeatures) {
            tenures.value = [];
            return;
        }
        try {
            tenures.value = await fetchWfsIntersect(
                CROWN_TENURES_LAYER,
                boundary as object,
                'SHAPE',
            );
        } catch {
            tenures.value = [];
        }
    },
    { immediate: true },
);

const fields = (data: ArchesDraftData): ReviewField[] => {
    const result = getServiceRequestInfoFields(data);
    if (tenures.value.length) {
        result.push({
            label: 'Intersecting Crown Tenures',
            type: 'table',
            columns: [
                { field: 'CROWN_LANDS_FILE', header: 'File' },
                { field: 'TENURE_TYPE', header: 'Type' },
                { field: 'TENURE_SUBTYPE', header: 'Subtype' },
                { field: 'TENURE_PURPOSE', header: 'Purpose' },
                { field: 'TENURE_STATUS', header: 'Status' },
                { field: 'TENURE_HOLDER_NAME', header: 'Holder' },
            ],
            rows: tenures.value.map((t) => t.properties),
        });
    }
    return result;
};

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
