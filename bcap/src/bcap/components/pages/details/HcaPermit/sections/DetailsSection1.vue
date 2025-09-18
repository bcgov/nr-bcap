<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";
import { getDisplayValue, isEmpty } from "@/bcap/util.ts";
import type { HcaPermitSchema, PermitIdentificationTile } from "@/bcap/schema/HcaPermitSchema.ts";
import type {
    AliasedNodeData,
} from "@/arches_component_lab/types.ts";
import "primeicons/primeicons.css";

const props = withDefaults(
    defineProps<{
        data: HcaPermitSchema | undefined;
        loading?: boolean;
        languageCode?: string;
    }>(),
    {
        languageCode: "en",
    },
);

const currentData = computed<PermitIdentificationTile | undefined>(() => {
    return props.data?.aliased_data?.permit_identification;
});
</script>

<template>
    <DetailsSection
        section-title="1. Permit Identification"
        :loading="props.loading"
        :visible="true"
    >
        <template #sectionContent>
            <dl v-if="currentData?.aliased_data">
                <dt v-if="currentData.aliased_data.permit_number && !isEmpty(currentData.aliased_data.permit_number)">Permit Number</dt>
                <dd v-if="currentData.aliased_data.permit_number && !isEmpty(currentData.aliased_data.permit_number)">
                    {{ getDisplayValue(currentData.aliased_data.permit_number) }}
                </dd>

                <dt v-if="currentData.aliased_data.hca_permit_type && !isEmpty(currentData.aliased_data.hca_permit_type)">HCA Permit Type</dt>
                <dd v-if="currentData.aliased_data.hca_permit_type && !isEmpty(currentData.aliased_data.hca_permit_type)">
                    {{ getDisplayValue(currentData.aliased_data.hca_permit_type) }}
                </dd>

                <dt v-if="currentData.aliased_data.permit_holder && !isEmpty(currentData.aliased_data.permit_holder)">Permit Holder</dt>
                <dd v-if="currentData.aliased_data.permit_holder && !isEmpty(currentData.aliased_data.permit_holder)">
                    {{ getDisplayValue(currentData.aliased_data.permit_holder) }}
                </dd>

                <dt v-if="currentData.aliased_data.issuing_agency && !isEmpty(currentData.aliased_data.issuing_agency)">Issuing Agency</dt>
                <dd v-if="currentData.aliased_data.issuing_agency && !isEmpty(currentData.aliased_data.issuing_agency)">
                    {{ getDisplayValue(currentData.aliased_data.issuing_agency) }}
                </dd>
            </dl>
            <div v-else>
                <p>No permit identification information available.</p>
            </div>
        </template>
    </DetailsSection>
</template>
