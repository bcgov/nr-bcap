<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";

import StandardDataTable from "@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue";
import type { SiteVisitSchema } from "@/bcap/schema/SiteVisitSchema.ts";

const props = withDefaults(
    defineProps<{ data: SiteVisitSchema | undefined }>(),
    {},
);
const details = computed(() => props.data?.aliased_data?.site_visit_details);
const teamTile = computed(
    () => details.value?.aliased_data?.site_visit_team_n1,
);
const teamMembers = computed(
    () => teamTile.value?.aliased_data?.team_member || [],
);

const teamColumns = [
    { field: "team_member", label: "Team Member" },
    { field: "member_roles", label: "Roles" },
    { field: "was_on_site", label: "Was On Site" },
];
</script>

<template>
    <DetailsSection
        section-title="3. Site Visit Details"
        :visible="true"
    >
        <template #sectionContent>
            <div>
                <dl>
                    <dt>3.1 Site Visit Type</dt>
                    <dd>
                        {{
                            details?.aliased_data?.site_visit_type
                                ?.display_value
                        }}
                    </dd>

                    <dt>3.2 Last Date of Site Visit</dt>
                    <dd>
                        {{
                            details?.aliased_data?.last_date_of_site_visit
                                ?.display_value
                        }}
                    </dd>

                    <dt>3.3 Project Description</dt>
                    <dd>
                        {{
                            details?.aliased_data?.project_description
                                ?.display_value
                        }}
                    </dd>

                    <dt>3.4 Associated Permit</dt>
                    <dd>
                        {{
                            details?.aliased_data?.associated_permit
                                ?.display_value
                        }}
                    </dd>

                    <dt>3.5 Archaeological Site</dt>
                    <dd>
                        {{
                            details?.aliased_data?.archaeological_site
                                ?.display_value
                        }}
                    </dd>

                    <dt>3.6 Affiliation</dt>
                    <dd>
                        {{ details?.aliased_data?.affiliation?.display_value }}
                    </dd>
                </dl>

                <h4>3.7 Site Visit Team</h4>
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
