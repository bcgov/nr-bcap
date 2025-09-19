<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";
import EmptyState from "@/bcap/components/EmptyState.vue";
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

const hasPermitInfo = computed(() => {
    const data = currentData.value?.aliased_data;
    return data && (
        !isEmpty(data.permit_number) ||
        !isEmpty(data.hca_permit_type) ||
        !isEmpty(data.permit_holder) ||
        !isEmpty(data.issuing_agency)
    );
});
</script>

<template>
    <DetailsSection
        section-title="1. Permit Identification"
        :loading="props.loading"
        :visible="true"
    >
        <template #sectionContent>
            <DetailsSection
                section-title="Permit Information"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasPermitInfo }"
            >
                <template #sectionContent>
                    <dl v-if="hasPermitInfo">
                        <dt v-if="!isEmpty(currentData?.aliased_data?.permit_number)">Permit Number</dt>
                        <dd v-if="!isEmpty(currentData?.aliased_data?.permit_number)">
                            {{ getDisplayValue(currentData?.aliased_data?.permit_number) }}
                        </dd>

                        <dt v-if="!isEmpty(currentData?.aliased_data?.hca_permit_type)">HCA Permit Type</dt>
                        <dd v-if="!isEmpty(currentData?.aliased_data?.hca_permit_type)">
                            {{ getDisplayValue(currentData?.aliased_data?.hca_permit_type) }}
                        </dd>

                        <dt v-if="!isEmpty(currentData?.aliased_data?.permit_holder)">Permit Holder</dt>
                        <dd v-if="!isEmpty(currentData?.aliased_data?.permit_holder)">
                            {{ getDisplayValue(currentData?.aliased_data?.permit_holder) }}
                        </dd>

                        <dt v-if="!isEmpty(currentData?.aliased_data?.issuing_agency)">Issuing Agency</dt>
                        <dd v-if="!isEmpty(currentData?.aliased_data?.issuing_agency)">
                            {{ getDisplayValue(currentData?.aliased_data?.issuing_agency) }}
                        </dd>
                    </dl>
                    <EmptyState
                        v-else
                        message="No permit identification information available."
                    />
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>
