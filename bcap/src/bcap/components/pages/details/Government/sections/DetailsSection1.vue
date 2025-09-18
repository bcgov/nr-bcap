<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";
import { getDisplayValue, isEmpty } from "@/bcap/util.ts";
import type { GovernmentSchema, GovernmentNameTile, GovernmentLocationTile } from "@/bcap/schema/GovernmentSchema.ts";
import type {
    AliasedNodeData,
} from "@/arches_component_lab/types.ts";
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
</script>

<template>
    <DetailsSection
        section-title="1. Government Information"
        :loading="props.loading"
        :visible="true"
    >
        <template #sectionContent>
            <DetailsSection
                section-title="1.1 Government Details"
                :visible="true"
            >
                <template #sectionContent>
                    <dl v-if="governmentName?.aliased_data">
                        <dt v-if="governmentName.aliased_data.government_name && !isEmpty(governmentName.aliased_data.government_name)">Government Name</dt>
                        <dd v-if="governmentName.aliased_data.government_name && !isEmpty(governmentName.aliased_data.government_name)">
                            {{ getDisplayValue(governmentName.aliased_data.government_name) }}
                        </dd>

                        <dt v-if="governmentName.aliased_data.government_type && !isEmpty(governmentName.aliased_data.government_type)">Government Type</dt>
                        <dd v-if="governmentName.aliased_data.government_type && !isEmpty(governmentName.aliased_data.government_type)">
                            {{ getDisplayValue(governmentName.aliased_data.government_type) }}
                        </dd>
                    </dl>
                    <div v-else>
                        <p>No government information available.</p>
                    </div>
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="1.2 Office Address"
                :visible="true"
            >
                <template #sectionContent>
                    <dl v-if="governmentLocation?.office_address?.aliased_data">
                        <dt v-if="governmentLocation.office_address.aliased_data.street_address && !isEmpty(governmentLocation.office_address.aliased_data.street_address)">Street Address</dt>
                        <dd v-if="governmentLocation.office_address.aliased_data.street_address && !isEmpty(governmentLocation.office_address.aliased_data.street_address)">
                            {{ getDisplayValue(governmentLocation.office_address.aliased_data.street_address) }}
                        </dd>

                        <dt v-if="governmentLocation.office_address.aliased_data.city && !isEmpty(governmentLocation.office_address.aliased_data.city)">City</dt>
                        <dd v-if="governmentLocation.office_address.aliased_data.city && !isEmpty(governmentLocation.office_address.aliased_data.city)">
                            {{ getDisplayValue(governmentLocation.office_address.aliased_data.city) }}
                        </dd>

                        <dt v-if="governmentLocation.office_address.aliased_data.province && !isEmpty(governmentLocation.office_address.aliased_data.province)">Province</dt>
                        <dd v-if="governmentLocation.office_address.aliased_data.province && !isEmpty(governmentLocation.office_address.aliased_data.province)">
                            {{ getDisplayValue(governmentLocation.office_address.aliased_data.province) }}
                        </dd>

                        <dt v-if="governmentLocation.office_address.aliased_data.postal_code && !isEmpty(governmentLocation.office_address.aliased_data.postal_code)">Postal Code</dt>
                        <dd v-if="governmentLocation.office_address.aliased_data.postal_code && !isEmpty(governmentLocation.office_address.aliased_data.postal_code)">
                            {{ getDisplayValue(governmentLocation.office_address.aliased_data.postal_code) }}
                        </dd>
                    </dl>
                    <div v-else>
                        <p>No office address information available.</p>
                    </div>
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="1.3 Government Boundary"
                :visible="true"
            >
                <template #sectionContent>
                    <dl v-if="governmentLocation?.government_boundary?.aliased_data">
                        <dt v-if="governmentLocation.government_boundary.aliased_data.government_boundary && !isEmpty(governmentLocation.government_boundary.aliased_data.government_boundary)">Government Boundary</dt>
                        <dd v-if="governmentLocation.government_boundary.aliased_data.government_boundary && !isEmpty(governmentLocation.government_boundary.aliased_data.government_boundary)">
                            {{ getDisplayValue(governmentLocation.government_boundary.aliased_data.government_boundary) }}
                        </dd>
                    </dl>
                    <div v-else>
                        <p>No government boundary information available.</p>
                    </div>
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>
