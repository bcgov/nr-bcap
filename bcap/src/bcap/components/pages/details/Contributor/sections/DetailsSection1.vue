<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";
import { getDisplayValue, isEmpty } from "@/bcap/util.ts";
import StandardDataTable from "@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue";
import type { ContributorSchema, ContributorTile } from "@/bcap/schema/ContributorSchema.ts";
import type {
    AliasedNodeData,
} from "@/arches_component_lab/types.ts";
import "primeicons/primeicons.css";

const props = withDefaults(
    defineProps<{
        data: ContributorSchema | undefined;
        loading?: boolean;
        languageCode?: string;
    }>(),
    {
        languageCode: "en",
    },
);

const currentData = computed<ContributorTile | undefined>(() => {
    return props.data?.aliased_data?.contributor;
});

const organizationColumns = [
    { field: "associated_organization", label: "Organization" },
    { field: "start_date", label: "Start Date" },
    { field: "end_date", label: "End Date" },
];
</script>

<template>
    <DetailsSection
        section-title="1. Contributor Information"
        :loading="props.loading"
        :visible="true"
    >
        <template #sectionContent>
            <DetailsSection
                section-title="1.1 Basic Information"
                :visible="true"
            >
                <template #sectionContent>
                    <dl v-if="currentData?.aliased_data">
                        <dt v-if="currentData.aliased_data.contributor_name && !isEmpty(currentData.aliased_data.contributor_name)">Contributor Name</dt>
                        <dd v-if="currentData.aliased_data.contributor_name && !isEmpty(currentData.aliased_data.contributor_name)">
                            {{ getDisplayValue(currentData.aliased_data.contributor_name) }}
                        </dd>

                        <dt v-if="currentData.aliased_data.first_name && !isEmpty(currentData.aliased_data.first_name)">First Name</dt>
                        <dd v-if="currentData.aliased_data.first_name && !isEmpty(currentData.aliased_data.first_name)">
                            {{ getDisplayValue(currentData.aliased_data.first_name) }}
                        </dd>

                        <dt v-if="currentData.aliased_data.contributor_type && !isEmpty(currentData.aliased_data.contributor_type)">Contributor Type</dt>
                        <dd v-if="currentData.aliased_data.contributor_type && !isEmpty(currentData.aliased_data.contributor_type)">
                            {{ getDisplayValue(currentData.aliased_data.contributor_type) }}
                        </dd>

                        <dt v-if="currentData.aliased_data.contributor_role && !isEmpty(currentData.aliased_data.contributor_role)">Contributor Role</dt>
                        <dd v-if="currentData.aliased_data.contributor_role && !isEmpty(currentData.aliased_data.contributor_role)">
                            {{ getDisplayValue(currentData.aliased_data.contributor_role) }}
                        </dd>

                        <dt v-if="currentData.aliased_data.inactive && !isEmpty(currentData.aliased_data.inactive)">Inactive</dt>
                        <dd v-if="currentData.aliased_data.inactive && !isEmpty(currentData.aliased_data.inactive)">
                            {{ getDisplayValue(currentData.aliased_data.inactive) }}
                        </dd>
                    </dl>
                    <div v-else>
                        <p>No contributor information available.</p>
                    </div>
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="1.2 Contact Information"
                :visible="true"
            >
                <template #sectionContent>
                    <dl v-if="currentData?.aliased_data">
                        <dt v-if="currentData.aliased_data.contact_email && !isEmpty(currentData.aliased_data.contact_email)">Email</dt>
                        <dd v-if="currentData.aliased_data.contact_email && !isEmpty(currentData.aliased_data.contact_email)">
                            {{ getDisplayValue(currentData.aliased_data.contact_email) }}
                        </dd>

                        <dt v-if="currentData.aliased_data.contact_phone_number && !isEmpty(currentData.aliased_data.contact_phone_number)">Phone Number</dt>
                        <dd v-if="currentData.aliased_data.contact_phone_number && !isEmpty(currentData.aliased_data.contact_phone_number)">
                            {{ getDisplayValue(currentData.aliased_data.contact_phone_number) }}
                        </dd>
                    </dl>
                    <div v-else>
                        <p>No contact information available.</p>
                    </div>
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="1.3 Associated Organizations"
                :visible="true"
            >
                <template #sectionContent>
                    <StandardDataTable
                        :table-data="props.data?.aliased_data?.associated_organization ?? []"
                        :column-definitions="organizationColumns"
                        title="Associated Organizations"
                        :initial-sort-field-index="1"
                    />
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>
