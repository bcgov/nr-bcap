<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";

import StandardDataTable from "@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue";
import type { SiteVisitSchema } from "@/bcap/schema/SiteVisitSchema.ts";

const props = withDefaults(
    defineProps<{
        data: SiteVisitSchema | undefined;
        sectionTitle?: string;
        loading?: boolean;
        visible?: boolean;
    }>(),
    { sectionTitle: "3. Site Visit Details", visible: true, loading: false },
);
const details = computed(() => props.data?.aliased_data?.site_visit_details);
const teamTile = computed(
    () => details.value?.aliased_data?.site_visit_team_n1,
);
const teamMembers = computed(
    () => teamTile.value?.aliased_data?.team_member || [],
);

const teamColumns = [
    { field: "team_member", label: "Name" },
    { field: "member_roles", label: "Roles" },
    { field: "was_on_site", label: "Was On Site" },
];
const siteVisitDetailsColumns = [
    { field: "site_visit_type", label: "Type" },
    { field: "last_date_of_site_visit", label: "Last Date" },
    { field: "project_description", label: "Project Description" },
    { field: "associated_permit", label: "Permit" },
    { field: "affiliation", label: "Affiliation" },
];
</script>

<template>
    <DetailsSection
        :section-title="props.sectionTitle"
        :visible="props.visible"
        :loading="props.loading"
    >
        <template #sectionContent>
            <div>
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
                    :table-data="details ? [details] : []"
                ></StandardDataTable>

                <dt>Site Visit Team</dt>
                <StandardDataTable
                    :table-data="teamMembers || []"
                    :column-definitions="teamColumns"
                />
            </div>
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
<style scoped></style>
