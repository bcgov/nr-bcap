<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";
import EmptyState from "@/bcap/components/EmptyState.vue";
import { getDisplayValue, isEmpty } from "@/bcap/util.ts";
import type {
    GovernmentSchema,
    GovernmentNameTile,
    GovernmentLocationTile,
} from "@/bcap/schema/GovernmentSchema.ts";
import type { AliasedNodeData } from "@/arches_component_lab/types.ts";
import "primeicons/primeicons.css";

const props = withDefaults(
    defineProps<{
        data: GovernmentSchema | undefined;
        loading?: boolean;
        languageCode?: string;
    }>(),
    {
        languageCode: "en",
    },
);

const governmentName = computed<GovernmentNameTile | undefined>(() => {
    return props.data?.aliased_data?.government_name;
});

const governmentLocation = computed<GovernmentLocationTile | undefined>(() => {
    return props.data?.aliased_data?.government_location;
});

const hasGovernmentDetails = computed(() => {
    const data = governmentName.value?.aliased_data;
    return (
        data &&
        (!isEmpty(data.government_name) || !isEmpty(data.government_type))
    );
});

const hasOfficeAddress = computed(() => {
    const data = governmentLocation.value?.office_address?.aliased_data;
    return (
        data &&
        (!isEmpty(data.street_address) ||
            !isEmpty(data.city) ||
            !isEmpty(data.province) ||
            !isEmpty(data.postal_code))
    );
});

const hasGovernmentBoundary = computed(() => {
    const data = governmentLocation.value?.government_boundary?.aliased_data;
    return data && !isEmpty(data.government_boundary);
});
</script>

<template>
    <DetailsSection
        section-title="1. Government Information"
        :loading="props.loading"
        :visible="true"
    >
        <template #sectionContent>
            <DetailsSection
                section-title="Government Details"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasGovernmentDetails }"
            >
                <template #sectionContent>
                    <dl v-if="hasGovernmentDetails">
                        <dt
                            v-if="
                                !isEmpty(
                                    governmentName?.aliased_data
                                        ?.government_name,
                                )
                            "
                        >
                            Government Name
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    governmentName?.aliased_data
                                        ?.government_name,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    governmentName?.aliased_data
                                        ?.government_name,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    governmentName?.aliased_data
                                        ?.government_type,
                                )
                            "
                        >
                            Government Type
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    governmentName?.aliased_data
                                        ?.government_type,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    governmentName?.aliased_data
                                        ?.government_type,
                                )
                            }}
                        </dd>
                    </dl>
                    <EmptyState
                        v-else
                        message="No government information available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Office Address"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasOfficeAddress }"
            >
                <template #sectionContent>
                    <dl v-if="hasOfficeAddress">
                        <dt
                            v-if="
                                !isEmpty(
                                    governmentLocation?.office_address
                                        ?.aliased_data?.street_address,
                                )
                            "
                        >
                            Street Address
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    governmentLocation?.office_address
                                        ?.aliased_data?.street_address,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    governmentLocation?.office_address
                                        ?.aliased_data?.street_address,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    governmentLocation?.office_address
                                        ?.aliased_data?.city,
                                )
                            "
                        >
                            City
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    governmentLocation?.office_address
                                        ?.aliased_data?.city,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    governmentLocation?.office_address
                                        ?.aliased_data?.city,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    governmentLocation?.office_address
                                        ?.aliased_data?.province,
                                )
                            "
                        >
                            Province
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    governmentLocation?.office_address
                                        ?.aliased_data?.province,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    governmentLocation?.office_address
                                        ?.aliased_data?.province,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    governmentLocation?.office_address
                                        ?.aliased_data?.postal_code,
                                )
                            "
                        >
                            Postal Code
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    governmentLocation?.office_address
                                        ?.aliased_data?.postal_code,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    governmentLocation?.office_address
                                        ?.aliased_data?.postal_code,
                                )
                            }}
                        </dd>
                    </dl>
                    <EmptyState
                        v-else
                        message="No office address information available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Government Boundary"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasGovernmentBoundary }"
            >
                <template #sectionContent>
                    <dl v-if="hasGovernmentBoundary">
                        <dt
                            v-if="
                                !isEmpty(
                                    governmentLocation?.government_boundary
                                        ?.aliased_data?.government_boundary,
                                )
                            "
                        >
                            Government Boundary
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    governmentLocation?.government_boundary
                                        ?.aliased_data?.government_boundary,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    governmentLocation?.government_boundary
                                        ?.aliased_data?.government_boundary,
                                )
                            }}
                        </dd>
                    </dl>
                    <EmptyState
                        v-else
                        message="No government boundary information available."
                    />
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>
