<script setup lang="ts">
import { computed, toRef } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import EmptyState from '@/bcap/components/EmptyState.vue';
import StandardDataTable from '@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue';
import { getDisplayValue, isEmpty } from '@/bcap/util.ts';
import {
    useTileEditLog,
    useSingleTileEditLog,
} from '@/bcap/composables/useTileEditLog.ts';
import type { EditLogData } from '@/bcgov_arches_common/types.ts';
import { EDIT_LOG_FIELDS } from '@/bcgov_arches_common/constants.ts';
import type { SiteVisitSchema } from '@/bcap/schema/SiteVisitSchema.ts';
import type { AliasedNodeData } from '@/arches_component_lab/types.ts';

const props = withDefaults(
    defineProps<{
        data: SiteVisitSchema | undefined;
        sectionTitle?: string;
        loading?: boolean;
        visible?: boolean;
        editLogData?: EditLogData;
    }>(),
    {
        sectionTitle: '3. Site Visit Details',
        visible: true,
        loading: false,
        editLogData: () => ({}),
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

const { processedData: teamMembersTableData } = useTileEditLog(
    teamMembers,
    toRef(props, 'editLogData'),
);

const { processedData: siteVisitDetailsData } = useSingleTileEditLog(
    details,
    toRef(props, 'editLogData'),
);

const siteVisitDetailsTableData = computed(() => {
    if (!siteVisitDetailsData.value) return [];

    return [
        {
            ...siteVisitDetailsData.value,
            site_visit_type:
                siteVisitDetailsData.value.aliased_data?.site_visit_type,
            last_date_of_site_visit:
                siteVisitDetailsData.value.aliased_data
                    ?.last_date_of_site_visit,
            first_date_of_site_visit:
                siteVisitDetailsData.value.aliased_data
                    ?.first_date_of_site_visit,
            project_description:
                siteVisitDetailsData.value.aliased_data?.project_description,
            associated_permit:
                siteVisitDetailsData.value.aliased_data?.associated_permit,
            affiliation: siteVisitDetailsData.value.aliased_data?.affiliation,
        },
    ];
});

const hasDetails = computed(() => details.value?.aliased_data);
const hasTeamMembers = computed(() => teamMembersTableData.value.length > 0);
const hasSiteFormAuthors = computed(
    () => siteFormAuthorsField.value && !isEmpty(siteFormAuthorsField.value),
);

const teamColumns = [
    { field: 'team_member', label: 'Name' },
    { field: 'member_roles', label: 'Role(s)' },
    { field: 'was_on_site', label: 'On Site' },
    { field: EDIT_LOG_FIELDS.ENTERED_ON, label: 'Entered On' },
    { field: EDIT_LOG_FIELDS.ENTERED_BY, label: 'Entered By' },
];

const siteVisitDetailsColumns = [
    { field: 'site_visit_type', label: 'Site Visit Type' },
    { field: 'last_date_of_site_visit', label: 'Last Date On Site' },
    { field: 'project_description', label: 'Site Visit Description' },
    { field: 'associated_permit', label: 'Associated Permit' },
    { field: 'affiliation', label: 'Affiliation' },
    { field: EDIT_LOG_FIELDS.ENTERED_ON, label: 'Entered On' },
    { field: EDIT_LOG_FIELDS.ENTERED_BY, label: 'Entered By' },
];
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
                        message="No team member information available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Site Form Author(s)"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasSiteFormAuthors }"
            >
                <template #sectionContent>
                    <div v-if="hasSiteFormAuthors">
                        <dl>
                            <dt>Site Form Author(s)</dt>
                            <dd>{{ getDisplayValue(siteFormAuthorsField) }}</dd>
                        </dl>
                    </div>
                    <EmptyState
                        v-else
                        message="No site form authors available."
                    />
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>

<style>
dl {
    display: flex;
    flex-direction: column;
    padding-bottom: 1rem;
}
dt {
    min-width: 20rem;
}
</style>
