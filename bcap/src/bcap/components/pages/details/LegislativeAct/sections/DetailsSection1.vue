<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";
import { getDisplayValue, isEmpty } from "@/bcap/util.ts";
import type { LegislativeActSchema, LegislativeActTile } from "@/bcap/schema/LegislativeActSchema.ts";
import type {
    AliasedNodeData,
} from "@/arches_component_lab/types.ts";
import "primeicons/primeicons.css";

const props = withDefaults(
    defineProps<{
        data: LegislativeActSchema | undefined;
        loading?: boolean;
        languageCode?: string;
    }>(),
    {
        languageCode: "en",
    },
);

const currentData = computed<LegislativeActTile | undefined>(() => {
    return props.data?.aliased_data?.legislative_act;
});
</script>

<template>
    <DetailsSection
        section-title="1. Legislative Act Information"
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
                        <dt v-if="currentData.aliased_data.act_name && !isEmpty(currentData.aliased_data.act_name)">Act Name</dt>
                        <dd v-if="currentData.aliased_data.act_name && !isEmpty(currentData.aliased_data.act_name)">
                            {{ getDisplayValue(currentData.aliased_data.act_name) }}
                        </dd>

                        <dt v-if="currentData.aliased_data.act_type && !isEmpty(currentData.aliased_data.act_type)">Act Type</dt>
                        <dd v-if="currentData.aliased_data.act_type && !isEmpty(currentData.aliased_data.act_type)">
                            {{ getDisplayValue(currentData.aliased_data.act_type) }}
                        </dd>

                        <dt v-if="currentData.aliased_data.jurisdiction && !isEmpty(currentData.aliased_data.jurisdiction)">Jurisdiction</dt>
                        <dd v-if="currentData.aliased_data.jurisdiction && !isEmpty(currentData.aliased_data.jurisdiction)">
                            {{ getDisplayValue(currentData.aliased_data.jurisdiction) }}
                        </dd>

                        <dt v-if="currentData.aliased_data.act_citation && !isEmpty(currentData.aliased_data.act_citation)">Citation</dt>
                        <dd v-if="currentData.aliased_data.act_citation && !isEmpty(currentData.aliased_data.act_citation)">
                            {{ getDisplayValue(currentData.aliased_data.act_citation) }}
                        </dd>

                        <dt v-if="currentData.aliased_data.responsible_ministry && !isEmpty(currentData.aliased_data.responsible_ministry)">Responsible Ministry</dt>
                        <dd v-if="currentData.aliased_data.responsible_ministry && !isEmpty(currentData.aliased_data.responsible_ministry)">
                            {{ getDisplayValue(currentData.aliased_data.responsible_ministry) }}
                        </dd>

                        <dt v-if="currentData.aliased_data.act_status && !isEmpty(currentData.aliased_data.act_status)">Status</dt>
                        <dd v-if="currentData.aliased_data.act_status && !isEmpty(currentData.aliased_data.act_status)">
                            {{ getDisplayValue(currentData.aliased_data.act_status) }}
                        </dd>
                    </dl>
                    <div v-else>
                        <p>No legislative act information available.</p>
                    </div>
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="1.2 Dates"
                :visible="true"
            >
                <template #sectionContent>
                    <dl v-if="currentData?.aliased_data">
                        <dt v-if="currentData.aliased_data.enactment_date && !isEmpty(currentData.aliased_data.enactment_date)">Enactment Date</dt>
                        <dd v-if="currentData.aliased_data.enactment_date && !isEmpty(currentData.aliased_data.enactment_date)">
                            {{ getDisplayValue(currentData.aliased_data.enactment_date) }}
                        </dd>

                        <dt v-if="currentData.aliased_data.repeal_date && !isEmpty(currentData.aliased_data.repeal_date)">Repeal Date</dt>
                        <dd v-if="currentData.aliased_data.repeal_date && !isEmpty(currentData.aliased_data.repeal_date)">
                            {{ getDisplayValue(currentData.aliased_data.repeal_date) }}
                        </dd>
                    </dl>
                    <div v-else>
                        <p>No date information available.</p>
                    </div>
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="1.3 Description"
                :visible="true"
            >
                <template #sectionContent>
                    <dl v-if="currentData?.aliased_data">
                        <dt v-if="currentData.aliased_data.act_description && !isEmpty(currentData.aliased_data.act_description)">Description</dt>
                        <dd v-if="currentData.aliased_data.act_description && !isEmpty(currentData.aliased_data.act_description)">
                            {{ getDisplayValue(currentData.aliased_data.act_description) }}
                        </dd>
                    </dl>
                    <div v-else>
                        <p>No description available.</p>
                    </div>
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>
