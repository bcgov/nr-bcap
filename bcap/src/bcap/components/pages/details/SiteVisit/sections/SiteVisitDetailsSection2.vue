<script setup lang="ts">
import { computed, toRef } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import EmptyState from '@/bcap/components/EmptyState.vue';
import { isAliasedNodeData } from '@/bcap/util.ts';
import StandardDataTable from '@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue';
import {
    useTileEditLog,
    useSingleTileEditLog,
} from '@/bcgov_arches_common/composables/useTileEditLog.ts';
import type { EditLogData } from '@/bcgov_arches_common/types.ts';
import { EDIT_LOG_FIELDS } from '@/bcgov_arches_common/constants.ts';
import type { SiteVisitSchema } from '@/bcap/schema/SiteVisitSchema.ts';

const props = withDefaults(
    defineProps<{
        data: SiteVisitSchema | undefined;
        loading?: boolean;
        editLogData?: EditLogData;
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

const { processedData: tempNumberData } = useSingleTileEditLog(
    tempNumber,
    toRef(props, 'editLogData'),
);

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
    { field: EDIT_LOG_FIELDS.ENTERED_ON, label: 'Entered On' },
    { field: EDIT_LOG_FIELDS.ENTERED_BY, label: 'Entered By' },
];

const tempNumberText = computed(() => {
    const tempNum = tempNumberData.value?.aliased_data?.temporary_number;
    return isAliasedNodeData(tempNum) ? tempNum.display_value : '';
});

const tempNumberAssignedBy = computed(() => {
    const assignedBy =
        tempNumberData.value?.aliased_data?.temporary_number_assigned_by;
    return isAliasedNodeData(assignedBy) ? assignedBy.display_value : '';
});

const tempNumberAssignedDate = computed(() => {
    const assignedDate =
        tempNumberData.value?.aliased_data?.temporary_number_assigned_date;
    return isAliasedNodeData(assignedDate) ? assignedDate.display_value : '';
});
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
                            <dt v-if="tempNumberText">Temporary Number</dt>
                            <dd v-if="tempNumberText">
                                {{ tempNumberText }}
                            </dd>
                            <dt v-if="tempNumberAssignedBy">Assigned By</dt>
                            <dd v-if="tempNumberAssignedBy">
                                {{ tempNumberAssignedBy }}
                            </dd>
                            <dt v-if="tempNumberAssignedDate">Assigned Date</dt>
                            <dd v-if="tempNumberAssignedDate">
                                {{ tempNumberAssignedDate }}
                            </dd>
                            <dt v-if="tempNumberData?.audit?.entered_on">
                                Entered On
                            </dt>
                            <dd v-if="tempNumberData?.audit?.entered_on">
                                {{ tempNumberData.audit.entered_on }}
                            </dd>
                            <dt v-if="tempNumberData?.audit?.entered_by">
                                Entered By
                            </dt>
                            <dd v-if="tempNumberData?.audit?.entered_by">
                                {{ tempNumberData.audit.entered_by }}
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
