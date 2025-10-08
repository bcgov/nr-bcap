<script setup lang="ts">
import { computed, toRef } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import EmptyState from '@/bcap/components/EmptyState.vue';
import { getDisplayValue, isAliasedNodeData, isEmpty } from '@/bcap/util.ts';
import { useSingleTileEditLog } from '@/bcgov_arches_common/composables/useTileEditLog.ts';
import type { EditLogData } from '@/bcgov_arches_common/types.ts';
import 'primeicons/primeicons.css';
import type { AncestralRemainsTile } from '@/bcap/schema/ArchaeologySiteSchema.ts';
import type { SiteVisitSchema } from '@/bcap/schema/SiteVisitSchema.ts';
import type { AliasedTileData } from '@/arches_component_lab/types.ts';

const props = withDefaults(
    defineProps<{
        data: AncestralRemainsTile | undefined;
        siteVisitData?: SiteVisitSchema[];
        loading?: boolean;
        languageCode?: string;
        forceCollapsed?: boolean;
        editLogData?: EditLogData;
    }>(),
    {
        siteVisitData: () => [],
        languageCode: 'en',
        loading: false,
        forceCollapsed: undefined,
        editLogData: () => ({}),
    },
);

const restrictedRemainsSource = computed(() => {
    return props.data?.aliased_data?.restricted_ancestral_remains_remark as
        | AliasedTileData
        | undefined;
});

const { processedData: restrictedRemainsData } = useSingleTileEditLog(
    restrictedRemainsSource,
    toRef(props, 'editLogData'),
);

const hasRestrictedRemainsInfo = computed(() => {
    return restrictedRemainsData.value?.aliased_data;
});

const restrictedRemarksText = computed(() => {
    const remarks =
        restrictedRemainsData.value?.aliased_data
            ?.restricted_ancestral_remains_remark;
    return isAliasedNodeData(remarks) ? getDisplayValue(remarks) : '';
});

const hasRestrictedRemarks = computed(() => {
    const remarks =
        restrictedRemainsData.value?.aliased_data
            ?.restricted_ancestral_remains_remark;
    return isAliasedNodeData(remarks) && !isEmpty(remarks);
});
</script>

<template>
    <DetailsSection
        section-title="7. Ancestral Remains"
        :loading="props.loading"
        :visible="true"
        :force-collapsed="props.forceCollapsed"
    >
        <template #sectionContent>
            <DetailsSection
                section-title="Restricted Ancestral Remains Information"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasRestrictedRemainsInfo }"
            >
                <template #sectionContent>
                    <dl v-if="hasRestrictedRemainsInfo">
                        <dt v-if="hasRestrictedRemarks">
                            Restricted Ancestral Remains Remarks
                        </dt>
                        <dd v-if="hasRestrictedRemarks">
                            {{ restrictedRemarksText }}
                        </dd>

                        <dt v-if="restrictedRemainsData?.audit?.entered_on">
                            Entered On
                        </dt>
                        <dd v-if="restrictedRemainsData?.audit?.entered_on">
                            {{ restrictedRemainsData.audit.entered_on }}
                        </dd>

                        <dt v-if="restrictedRemainsData?.audit?.entered_by">
                            Entered By
                        </dt>
                        <dd v-if="restrictedRemainsData?.audit?.entered_by">
                            {{ restrictedRemainsData.audit.entered_by }}
                        </dd>
                    </dl>
                    <EmptyState
                        v-else
                        message="No restricted ancestral remains information available."
                    />
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>
