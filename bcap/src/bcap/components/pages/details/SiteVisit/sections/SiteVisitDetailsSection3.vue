<script setup lang="ts">
import { computed, toRef } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import EmptyState from '@/bcap/components/EmptyState.vue';
import StandardDataTable from '@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue';
import { getDisplayValue, isEmpty } from '@/bcap/util.ts';
import { useResourceData } from '@/bcap/composables/useResourceData.ts';
import {
    useTileEditLog,
    useSingleTileEditLog,
} from '@/bcgov_arches_common/composables/useTileEditLog.ts';
import type { EditLogData } from '@/bcgov_arches_common/types.ts';
import { EDIT_LOG_FIELDS } from '@/bcgov_arches_common/constants.ts';
import type { SiteVisitSchema } from '@/bcap/schema/SiteVisitSchema.ts';
import type { HcaPermitSchema } from '@/bcap/schema/HcaPermitSchema.ts';
import type { AliasedNodeData } from '@/arches_component_lab/types.ts';

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
const teamTile = computed(
    () => details.value?.aliased_data?.site_visit_team_n1,
);
const teamMembers = computed(
    () => teamTile.value?.aliased_data?.team_member || [],
);
const siteFormAuthorsField = computed(() => {
    return details.value?.aliased_data?.site_form_authors as
        | AliasedNodeData
        | undefined;
});

const associatedPermitId = computed(() => {
    const permitField = details.value?.aliased_data?.associated_permit;
    return permitField?.details?.[0]?.resource_id;
});

const { data: permitData } = useResourceData<HcaPermitSchema>(
    'hca_permit',
    associatedPermitId,
);

const permitDetails = computed(() => {
    return permitData.value?.aliased_data?.permit_identification?.aliased_data;
});

const { processedData: teamMembersTableData } = useTileEditLog(
    teamMembers,
    toRef(props, 'editLogData'),
);

const { processedData: siteVisitDetailsData } = useSingleTileEditLog(
    details,
    toRef(props, 'editLogData'),
);

const permittedValue = computed(() => {
    const nonPermittedField =
        siteVisitDetailsData.value?.aliased_data?.nonpermitted_site_visit;

    if (nonPermittedField && 'node_value' in nonPermittedField) {
        const nonPermitted = nonPermittedField.node_value;
        if (nonPermitted === undefined || nonPermitted === null)
            return 'Unknown';

        return nonPermitted ? 'No' : 'Yes';
    }

    return 'Unknown';
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
            permit_number: permitDetails.value?.permit_number || {
                node_value: null,
                display_value: '',
                details: [],
            },
            permit_type: permitDetails.value?.hca_permit_type || {
                node_value: null,
                display_value: '',
                details: [],
            },
            permit_holder: permitDetails.value?.permit_holder || {
                node_value: null,
                display_value: '',
                details: [],
            },
            issuing_agency: permitDetails.value?.issuing_agency || {
                node_value: null,
                display_value: '',
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
    { field: 'site_visit_type', label: 'Site Visit Type' },
    { field: 'last_date_of_site_visit', label: 'Last Date On Site' },
    { field: 'project_description', label: 'Site Visit Description' },
    { field: 'permitted', label: 'Permitted' },
    { field: 'permit_number', label: 'Permit Number' },
    { field: 'permit_type', label: 'Permit Type' },
    { field: 'permit_holder', label: 'Permit Holder' },
    { field: 'affiliation', label: 'Affiliation' },
    { field: 'issuing_agency', label: 'Issuing Agency' },
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
                        <dl>
                            <dt>Archaeological Site</dt>
                            <dd>
                                {{
                                    details?.aliased_data?.archaeological_site
                                        ?.display_value
                                }}
                            </dd>
                        </dl>

                        <StandardDataTable
                            :column-definitions="siteVisitDetailsColumns"
                            :table-data="siteVisitDetailsTableData"
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
