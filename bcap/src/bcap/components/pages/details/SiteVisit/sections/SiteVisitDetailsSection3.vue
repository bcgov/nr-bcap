<script setup lang="ts">
import { computed, toRef, type Ref } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import EmptyState from '@/bcap/components/EmptyState.vue';
import StandardDataTable from '@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue';
import { getDisplayValue, isEmpty } from '@/bcap/util.ts';
import type { ApiHcaPermitListResponse } from '@/bcap/client/types.gen.ts';
import { useResourceList } from '@/bcap/composables/useResourceData.ts';
import {
    useTileEditLog,
    useSingleTileEditLog,
} from '@/bcgov_arches_common/composables/useTileEditLog.ts';
import type { EditLogData } from '@/bcgov_arches_common/types.ts';
import { EDIT_LOG_FIELDS } from '@/bcgov_arches_common/constants.ts';
import type { SiteVisitSchema } from '@/bcap/schema/SiteVisitSchema.ts';
import type {
    AliasedNodeData,
    AliasedTileData,
} from '@/arches_vue_components/types.ts';

const props = withDefaults(
    defineProps<{
        data: SiteVisitSchema | undefined;
        sectionTitle?: string;
        loading?: boolean;
        visible?: boolean;
        editLogData?: EditLogData;
        showAuditFields?: boolean;
    }>(),
    {
        sectionTitle: '3. Site Visit Details',
        visible: true,
        loading: false,
        editLogData: () => ({}),
        showAuditFields: false,
    },
);

const details = computed(() => props.data?.aliased_data?.site_visit_details);
const teamTile = computed(() => details.value?.aliased_data?.site_visit_team);
const teamMembers = computed(
    () => teamTile.value?.aliased_data?.team_member || [],
);
const siteFormAuthorsField = computed(() => {
    return details.value?.aliased_data?.site_form_authors as
        AliasedNodeData | undefined;
});

const associatedPermitIds = computed(() => {
    const permitField = details.value?.aliased_data?.associated_permit;
    return (permitField?.details ?? []).map((detail) => detail.resource_id);
});

const { data: permitData } = useResourceList<Ref<ApiHcaPermitListResponse>>(
    'hca_permit',
    associatedPermitIds,
);

const permitDetails = computed(() => {
    return (permitData?.value?.results.map(
        (permit) => permit.aliased_data?.permit_identification,
    ) || []) as AliasedTileData[];
});

const { processedData: teamMembersTableData } = useTileEditLog(
    teamMembers,
    toRef(props, 'editLogData'),
);

const { processedData: permitDetailsTableData } = useTileEditLog(
    permitDetails,
    toRef(props, 'editLogData'),
);

const { processedData: siteVisitDetailsData } = useSingleTileEditLog(
    details,
    toRef(props, 'editLogData'),
);

const permittedValue = computed(() => {
    const permittedField =
        siteVisitDetailsData.value?.aliased_data?.is_site_visit_permitted;

    if (permittedField && 'node_value' in permittedField) {
        const permitted = permittedField.node_value;
        if (permitted === undefined || permitted === null) return '';

        return permitted ? 'Yes' : 'No';
    }

    return '';
});

const siteVisitDetailsTableData = computed(() => {
    if (!siteVisitDetailsData.value) return [];

    const row = {
        ...siteVisitDetailsData.value,
        [EDIT_LOG_FIELDS.ENTERED_ON]:
            siteVisitDetailsData.value?.audit?.entered_on,
        [EDIT_LOG_FIELDS.ENTERED_BY]:
            siteVisitDetailsData.value?.audit?.entered_by,
        aliased_data: {
            ...siteVisitDetailsData.value.aliased_data,
            permitted: {
                node_value: permittedValue.value,
                display_value: permittedValue.value,
                details: [],
            },
        },
    };

    return [row];
});

const hasDetails = computed(() => details.value?.aliased_data);
const hasTeamMembers = computed(() => teamMembersTableData.value.length > 0);
const hasSiteFormAuthors = computed(
    () => siteFormAuthorsField.value && !isEmpty(siteFormAuthorsField.value),
);

const teamColumns = computed(() => [
    { field: 'team_member', label: 'Name' },
    { field: 'member_roles', label: 'Role(s)' },
    { field: 'was_on_site', label: 'On Site' },
    {
        field: EDIT_LOG_FIELDS.ENTERED_ON,
        label: 'Entered On',
        visible: props.showAuditFields,
    },
    {
        field: EDIT_LOG_FIELDS.ENTERED_BY,
        label: 'Entered By',
        visible: props.showAuditFields,
    },
]);

const siteVisitDetailsColumns = computed(() => [
    { field: 'archaeological_site', label: 'Archaeological Site' },
    { field: 'site_visit_type', label: 'Site Visit Type' },
    { field: 'last_date_of_site_visit', label: 'Last Date On Site' },
    {
        field: 'project_description',
        label: 'Site Visit Description',
        isHtml: true,
    },
    { field: 'permitted', label: 'Permitted' },
    {
        field: EDIT_LOG_FIELDS.ENTERED_ON,
        label: 'Entered On',
        visible: props.showAuditFields,
    },
    {
        field: EDIT_LOG_FIELDS.ENTERED_BY,
        label: 'Entered By',
        visible: props.showAuditFields,
    },
]);

const permitDetailsColumns = computed(() => [
    { field: 'permit_number', label: 'Permit Number' },
    { field: 'permit_type', label: 'Permit Type' },
    { field: 'permit_holder', label: 'Permit Holder' },
    { field: 'affiliation', label: 'Affiliation' },
    { field: 'issuing_agency', label: 'Issuing Agency' },
]);
</script>

<template>
    <DetailsSection
        :section-title="props.sectionTitle"
        :visible="props.visible"
        :loading="props.loading"
    >
        <template #sectionContent>
            <DetailsSection
                section-title="Site Visit Details"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasDetails }"
            >
                <template #sectionContent>
                    <div v-if="details">
                        <StandardDataTable
                            :column-definitions="siteVisitDetailsColumns"
                            :table-data="siteVisitDetailsTableData"
                        />
                        <StandardDataTable
                            :column-definitions="permitDetailsColumns"
                            :table-data="permitDetailsTableData"
                        />
                    </div>
                    <EmptyState
                        v-else
                        message="No site visit details available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Site Form Authors"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasSiteFormAuthors }"
            >
                <template #sectionContent>
                    <div v-if="hasSiteFormAuthors">
                        <dl>
                            <dt>Authors</dt>
                            <dd>
                                {{ getDisplayValue(siteFormAuthorsField) }}
                            </dd>
                        </dl>
                    </div>
                    <EmptyState
                        v-else
                        message="No site form authors available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Site Visit Team"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasTeamMembers }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasTeamMembers"
                        :table-data="teamMembersTableData"
                        :column-definitions="teamColumns"
                    />
                    <EmptyState
                        v-else
                        message="No team members available."
                    />
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>

<style scoped></style>
