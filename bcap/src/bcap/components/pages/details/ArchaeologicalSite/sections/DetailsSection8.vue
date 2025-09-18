<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";
import { getDisplayValue, isEmpty } from "@/bcap/util.ts";
import StandardDataTable from "@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue";
import "primeicons/primeicons.css";
import type { RemarksAndRestrictedInformationTile } from "@/bcap/schema/ArchaeologySiteSchema.ts";

const props = withDefaults(
    defineProps<{
        data: RemarksAndRestrictedInformationTile | undefined;
        siteVisitData?: any[];
        loading?: boolean;
        languageCode?: string;
    }>(),
    {
        loading: false,
        languageCode: "en",
    },
);

const currentData = computed<RemarksAndRestrictedInformationTile | undefined>(
    (): RemarksAndRestrictedInformationTile | undefined => {
        return props.data?.aliased_data as
            | RemarksAndRestrictedInformationTile
            | undefined;
    },
);

const generalRemarkColumns = [
    { field: "general_remark_date", label: "Date" },
    { field: "general_remark", label: "Remark" },
    { field: "general_remark_source", label: "Source" },
];

const restrictedRemarkColumns = [
    { field: "restricted_remark", label: "Restricted Remarks" },
    { field: "restricted_entry_date", label: "Entered On" },
    { field: "restricted_person", label: "Entered By" },
];

const hcaContraventionColumns = [
    { field: "inventory_remarks", label: "Inventory Remarks" },
    { field: "address", label: "Address" },
    { field: "pid", label: "PID" },
    { field: "nros_file_number", label: "NROS File #" },
    { field: "entered_on", label: "Entered On" },
    { field: "entered_by", label: "Entered By" },
];

const convictionColumns = [
    { field: "conviction_date", label: "Conviction Date" },
    { field: "inventory_remarks", label: "Inventory Remarks" },
    { field: "entered_on", label: "Entered On" },
    { field: "entered_by", label: "Entered By" },
];

const recorderRecommendationColumns = [
    { field: "recorders_recommendation", label: "Recorder's Recommendation" },
];

const archaeologyBranchRecommendationColumns = [
    { field: "archaeology_branch_recommendations", label: "Archaeology Branch Recommendations" },
    { field: "entered_on", label: "Entered On" },
    { field: "entered_by", label: "Entered By" },
];

const keywordsData = computed(() => {
    return currentData.value?.remark_keyword || [];
});

const restrictedInfoData = computed(() => {
    return currentData.value?.restricted_information_n1 || currentData.value?.restricted_information || [];
});

const aggregateRecorderRecommendations = computed(() => {
    if (!props.siteVisitData?.length) return [];

    const recommendations: any[] = [];

    props.siteVisitData.forEach(visit => {
        const visitRecommendations = visit.aliased_data?.remarks_and_recommendations?.aliased_data?.recommendation;
        if (visitRecommendations && Array.isArray(visitRecommendations)) {
            recommendations.push(...visitRecommendations);
        }
    });

    return recommendations;
});

const archaeologyBranchRecommendations = computed(() => {
    return currentData.value?.archaeology_branch_recommendations || [];
});
</script>

<template>
    <DetailsSection
        section-title="8. Remarks & Restricted Information"
        :loading="props.loading"
        :visible="true"
    >
        <template #sectionContent>
            <DetailsSection
                section-title="8.1 Keywords"
                :visible="true"
            >
                <template #sectionContent>
                    <div v-if="keywordsData.length">
                        <div v-for="(keyword, index) in keywordsData" :key="index" class="keyword-item">
                            {{ getDisplayValue(keyword) }}
                        </div>
                    </div>
                    <div v-else>
                        <p>No keywords available.</p>
                    </div>
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="8.2 General Remarks"
                :visible="true"
            >
                <template #sectionContent>
                    <StandardDataTable
                        :table-data="currentData?.general_remark_information ?? []"
                        :column-definitions="generalRemarkColumns"
                        title="General Remarks"
                        :initial-sort-field-index="0"
                    />
                    <div v-if="!currentData?.general_remark_information?.length">
                        <p>No general remarks available.</p>
                    </div>
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="8.3 Restricted Information"
                :visible="true"
            >
                <template #sectionContent>
                    <StandardDataTable
                        :table-data="restrictedInfoData"
                        :column-definitions="restrictedRemarkColumns"
                        title="Restricted Information"
                        :initial-sort-field-index="1"
                    />
                    <div v-if="!restrictedInfoData.length">
                        <p>No restricted information available.</p>
                    </div>
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="8.4 Documents"
                :visible="true"
            >
                <template #sectionContent>
                    <div v-if="!isEmpty(currentData?.contravention_document) || !isEmpty(currentData?.restricted_document)">
                        <dl>
                            <dt v-if="!isEmpty(currentData?.contravention_document)">Contravention Documents</dt>
                            <dd v-if="!isEmpty(currentData?.contravention_document)">
                                {{ getDisplayValue(currentData?.contravention_document) }}
                            </dd>

                            <dt v-if="!isEmpty(currentData?.restricted_document)">Restricted Documents</dt>
                            <dd v-if="!isEmpty(currentData?.restricted_document)">
                                {{ getDisplayValue(currentData?.restricted_document) }}
                            </dd>
                        </dl>
                    </div>
                    <div v-else>
                        <p>No documents available.</p>
                    </div>
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="8.5 HCA Contraventions"
                :visible="true"
            >
                <template #sectionContent>
                    <DetailsSection
                        section-title="8.5.1 Contraventions"
                        :visible="true"
                    >
                        <template #sectionContent>
                            <StandardDataTable
                                :table-data="currentData?.hca_contravention ?? []"
                                :column-definitions="hcaContraventionColumns"
                                title="HCA Contraventions"
                                :initial-sort-field-index="4"
                            />
                            <div v-if="!currentData?.hca_contravention?.length">
                                <p>No HCA contraventions recorded.</p>
                            </div>
                        </template>
                    </DetailsSection>

                    <DetailsSection
                        section-title="8.5.2 Convictions"
                        :visible="true"
                    >
                        <template #sectionContent>
                            <StandardDataTable
                                :table-data="currentData?.conviction ?? []"
                                :column-definitions="convictionColumns"
                                title="HCA Convictions"
                                :initial-sort-field-index="0"
                            />
                            <div v-if="!currentData?.conviction?.length">
                                <p>No HCA convictions recorded.</p>
                            </div>
                        </template>
                    </DetailsSection>
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>

<style scoped>
dl {
    display: flex;
    flex-direction: column;
    padding-bottom: 1rem;
}
dt {
    min-width: 20rem;
    padding-top: 0.75rem;
    font-weight: 600;
}
dd {
    padding-left: 1rem;
}
.keyword-item {
    padding: 0.25rem 0;
    border-left: 3px solid #007bff;
    padding-left: 0.75rem;
    margin-bottom: 0.5rem;
    background-color: #f8f9fa;
}
</style>
