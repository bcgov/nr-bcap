<script setup lang="ts">
import { computed, toRef } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import EmptyState from '@/bcap/components/EmptyState.vue';
import { getDisplayValue, isEmpty } from '@/bcap/util.ts';
import { useSingleTileEditLog } from '@/bcap/composables/useTileEditLog.ts';
import 'primeicons/primeicons.css';
import type { AncestralRemainsTile } from '@/bcap/schema/ArchaeologySiteSchema.ts';
import type { SiteVisitSchema } from '@/bcap/schema/SiteVisitSchema.ts';
import type { AliasedTileData, AliasedNodeData } from '@/arches_component_lab/types.ts';

const props = withDefaults(
    defineProps<{
        data: AncestralRemainsTile | undefined;
        siteVisitData?: SiteVisitSchema[];
        loading?: boolean;
        languageCode?: string;
        forceCollapsed?: boolean;
        editLogData?: Record<string, { entered_on: string | null; entered_by: string | null }>;
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
    return props.data?.aliased_data?.restricted_ancestral_remains_remark as AliasedTileData | undefined;
});

const { processedData: restrictedRemainsDataRaw } = useSingleTileEditLog(
    restrictedRemainsSource,
    toRef(props, 'editLogData'),
    {
        enteredOnField: 'remains_remark_entry_date',
        enteredByField: 'remains_remark_made_by'
    }
);

const restrictedRemainsData = computed(() => {
    const data = restrictedRemainsDataRaw.value;
    if (!data) return null;

    return {
        ...data,
        aliased_data: {
            ...data.aliased_data,
            remains_remark_entry_date: data.aliased_data?.remains_remark_entry_date as AliasedNodeData | undefined,
            remains_remark_made_by: data.aliased_data?.remains_remark_made_by as AliasedNodeData | undefined,
            restricted_ancestral_remains_remark: data.aliased_data?.restricted_ancestral_remains_remark as AliasedNodeData | undefined
        }
    };
});

const hasRestrictedRemainsInfo = computed(() => {
    return restrictedRemainsData.value?.aliased_data;
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
                        <dt
                            v-if="
                                !isEmpty(
                                    restrictedRemainsData?.aliased_data
                                        ?.restricted_ancestral_remains_remark,
                                )
                            "
                        >
                            Restricted Ancestral Remains Remarks
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    restrictedRemainsData?.aliased_data
                                        ?.restricted_ancestral_remains_remark,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    restrictedRemainsData?.aliased_data
                                        ?.restricted_ancestral_remains_remark,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                restrictedRemainsData?.aliased_data?.remains_remark_entry_date?.display_value
                            "
                        >
                            Entered On
                        </dt>
                        <dd
                            v-if="
                                restrictedRemainsData?.aliased_data?.remains_remark_entry_date?.display_value
                            "
                        >
                            {{
                                restrictedRemainsData.aliased_data.remains_remark_entry_date.display_value
                            }}
                        </dd>

                        <dt
                            v-if="
                                restrictedRemainsData?.aliased_data?.remains_remark_made_by?.display_value
                            "
                        >
                            Entered By
                        </dt>
                        <dd
                            v-if="
                                restrictedRemainsData?.aliased_data?.remains_remark_made_by?.display_value
                            "
                        >
                            {{
                                restrictedRemainsData.aliased_data.remains_remark_made_by.display_value
                            }}
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
