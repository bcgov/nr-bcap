<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";
import EmptyState from "@/bcap/components/EmptyState.vue";
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

const hasBasicInfo = computed(() => {
    const data = currentData.value?.aliased_data;
    return data && (
        !isEmpty(data.contributor_name) ||
        !isEmpty(data.first_name) ||
        !isEmpty(data.contributor_type) ||
        !isEmpty(data.contributor_role) ||
        !isEmpty(data.inactive)
    );
});

const hasContactInfo = computed(() => {
    const data = currentData.value?.aliased_data;
    return data && (
        !isEmpty(data.contact_email) ||
        !isEmpty(data.contact_phone_number)
    );
});

const hasOrganizations = computed(() => {
    return props.data?.aliased_data?.associated_organization &&
           props.data.aliased_data.associated_organization.length > 0;
});
</script>

<template>
    <DetailsSection
        section-title="1. Contributor Information"
        :loading="props.loading"
        :visible="true"
    >
        <template #sectionContent>
            <DetailsSection
                section-title="Basic Information"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasBasicInfo }"
            >
                <template #sectionContent>
                    <dl v-if="hasBasicInfo">
                        <dt v-if="!isEmpty(currentData?.aliased_data?.contributor_name)">Contributor Name</dt>
                        <dd v-if="!isEmpty(currentData?.aliased_data?.contributor_name)">
                            {{ getDisplayValue(currentData?.aliased_data?.contributor_name) }}
                        </dd>

                        <dt v-if="!isEmpty(currentData?.aliased_data?.first_name)">First Name</dt>
                        <dd v-if="!isEmpty(currentData?.aliased_data?.first_name)">
                            {{ getDisplayValue(currentData?.aliased_data?.first_name) }}
                        </dd>

                        <dt v-if="!isEmpty(currentData?.aliased_data?.contributor_type)">Contributor Type</dt>
                        <dd v-if="!isEmpty(currentData?.aliased_data?.contributor_type)">
                            {{ getDisplayValue(currentData?.aliased_data?.contributor_type) }}
                        </dd>

                        <dt v-if="!isEmpty(currentData?.aliased_data?.contributor_role)">Contributor Role</dt>
                        <dd v-if="!isEmpty(currentData?.aliased_data?.contributor_role)">
                            {{ getDisplayValue(currentData?.aliased_data?.contributor_role) }}
                        </dd>

                        <dt v-if="!isEmpty(currentData?.aliased_data?.inactive)">Inactive</dt>
                        <dd v-if="!isEmpty(currentData?.aliased_data?.inactive)">
                            {{ getDisplayValue(currentData?.aliased_data?.inactive) }}
                        </dd>
                    </dl>
                    <EmptyState
                        v-else
                        message="No contributor information available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Contact Information"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasContactInfo }"
            >
                <template #sectionContent>
                    <dl v-if="hasContactInfo">
                        <dt v-if="!isEmpty(currentData?.aliased_data?.contact_email)">Email</dt>
                        <dd v-if="!isEmpty(currentData?.aliased_data?.contact_email)">
                            {{ getDisplayValue(currentData?.aliased_data?.contact_email) }}
                        </dd>

                        <dt v-if="!isEmpty(currentData?.aliased_data?.contact_phone_number)">Phone Number</dt>
                        <dd v-if="!isEmpty(currentData?.aliased_data?.contact_phone_number)">
                            {{ getDisplayValue(currentData?.aliased_data?.contact_phone_number) }}
                        </dd>
                    </dl>
                    <EmptyState
                        v-else
                        message="No contact information available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Associated Organizations"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasOrganizations }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasOrganizations"
                        :table-data="props.data?.aliased_data?.associated_organization ?? []"
                        :column-definitions="organizationColumns"
                        title="Associated Organizations"
                        :initial-sort-field-index="1"
                    />
                    <EmptyState
                        v-else
                        message="No associated organizations recorded."
                    />
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>
