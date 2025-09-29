<script setup lang="ts">
import { computed, toRef } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import EmptyState from '@/bcap/components/EmptyState.vue';
import StandardDataTable from '@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue';
import {
    useTileEditLog,
    useSingleTileEditLog,
} from '@/bcap/composables/useTileEditLog.ts';
import type { SiteVisitSchema } from '@/bcap/schema/SiteVisitSchema.ts';
import type { AliasedNodeData } from '@/arches_component_lab/types.ts';

const props = withDefaults(
    defineProps<{
        data: SiteVisitSchema | undefined;
        loading?: boolean;
        editLogData?: Record<
            string,
            { entered_on: string | null; entered_by: string | null }
        >;
    }>(),
    {
        loading: false,
        editLogData: () => ({}),
    },
);

const idTile = computed(() => props.data?.aliased_data?.identification);
const tempNumber = computed(() => idTile.value?.aliased_data?.temporary_number);
const newNames = computed(
    () => idTile.value?.aliased_data?.new_site_names || [],
);

const { processedData: newNamesTableData } = useTileEditLog(
    newNames,
    toRef(props, 'editLogData'),
);

const { processedData: tempNumberDataRaw } = useSingleTileEditLog(
    tempNumber,
    toRef(props, 'editLogData'),
);

const tempNumberData = computed(() => {
    const data = tempNumberDataRaw.value;
    if (!data) return null;

    return {
        ...data,
        aliased_data: {
            ...data.aliased_data,
            entered_on: data.aliased_data?.entered_on as
                | AliasedNodeData
                | undefined,
            entered_by: data.aliased_data?.entered_by as
                | AliasedNodeData
                | undefined,
            temporary_number: data.aliased_data?.temporary_number as
                | AliasedNodeData
                | undefined,
            temporary_number_assigned_by: data.aliased_data
                ?.temporary_number_assigned_by as AliasedNodeData | undefined,
            temporary_number_assigned_date: data.aliased_data
                ?.temporary_number_assigned_date as AliasedNodeData | undefined,
        },
    };
});

const hasTemporaryNumber = computed(() => {
    return tempNumber.value?.aliased_data?.temporary_number?.node_value;
});

const hasNewNames = computed(() => {
    return newNamesTableData.value && newNamesTableData.value.length > 0;
});

const newNameColumns = [
    { field: 'name', label: 'Site Name' },
    { field: 'name_type', label: 'Site Name Type' },
    { field: 'name_remarks', label: 'Site Name Remarks' },
    { field: 'assigned_or_reported_date', label: 'Date Assigned or Reported' },
    { field: 'assigned_or_reported_by', label: 'Assigned or Reported By' },
    { field: 'entered_on', label: 'Entered On' },
    { field: 'entered_by', label: 'Entered By' },
];
</script>

<template>
    <DetailsSection
        section-title="2. Identification"
        :visible="true"
        :loading="props.loading"
    >
        <template #sectionContent>
            <DetailsSection
                section-title="Temporary Numbers"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasTemporaryNumber }"
            >
                <template #sectionContent>
                    <div v-if="tempNumberData">
                        <dl>
                            <dt>Temporary Number</dt>
                            <dd>
                                {{
                                    tempNumberData?.aliased_data
                                        ?.temporary_number?.display_value
                                }}
                            </dd>
                            <dt>Assigned By</dt>
                            <dd>
                                {{
                                    tempNumberData?.aliased_data
                                        ?.temporary_number_assigned_by
                                        ?.display_value
                                }}
                            </dd>
                            <dt>Assigned Date</dt>
                            <dd>
                                {{
                                    tempNumberData?.aliased_data
                                        ?.temporary_number_assigned_date
                                        ?.display_value
                                }}
                            </dd>
                            <dt
                                v-if="
                                    tempNumberData?.aliased_data?.entered_on
                                        ?.display_value
                                "
                            >
                                Entered On
                            </dt>
                            <dd
                                v-if="
                                    tempNumberData?.aliased_data?.entered_on
                                        ?.display_value
                                "
                            >
                                {{
                                    tempNumberData.aliased_data.entered_on
                                        .display_value
                                }}
                            </dd>
                            <dt
                                v-if="
                                    tempNumberData?.aliased_data?.entered_by
                                        ?.display_value
                                "
                            >
                                Entered By
                            </dt>
                            <dd
                                v-if="
                                    tempNumberData?.aliased_data?.entered_by
                                        ?.display_value
                                "
                            >
                                {{
                                    tempNumberData.aliased_data.entered_by
                                        .display_value
                                }}
                            </dd>
                        </dl>
                    </div>
                    <EmptyState
                        v-else
                        message="No temporary number assigned."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="New Site Names"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasNewNames }"
            >
                <template #sectionContent>
                    <div v-if="hasNewNames">
                        <StandardDataTable
                            :table-data="newNamesTableData"
                            :column-definitions="newNameColumns"
                        />
                    </div>
                    <EmptyState
                        v-else
                        message="No new site names available."
                    />
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>

<style scoped></style>
