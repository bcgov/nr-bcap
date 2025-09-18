<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";
import { getDisplayValue, isEmpty } from "@/bcap/util.ts";
import StandardDataTable from "@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue";
import type { HriaDiscontinuedDataSchema } from "@/bcap/schema/HriaDiscontinuedDataSchema.ts";
import type {
    AliasedNodeData,
} from "@/arches_component_lab/types.ts";
import "primeicons/primeicons.css";

const props = withDefaults(
    defineProps<{
        data: HriaDiscontinuedDataSchema | undefined;
        loading?: boolean;
        languageCode?: string;
    }>(),
    {
        languageCode: "en",
    },
);

const currentData = computed(() => {
    return props.data?.aliased_data;
});

const jurisdictionTenureColumns = [
    { field: "site_jurisdiction", label: "Site Jurisdiction" },
    { field: "tenure_type", label: "Tenure Type" },
    { field: "tenure_identifier", label: "Tenure Identifier" },
    { field: "tenure_remarks", label: "Tenure Remarks" },
    { field: "jurisdiction_entered_date", label: "Entered Date" },
    { field: "jurisdiction_entered_by", label: "Entered By" },
];

const chronologyColumns = [
    { field: "determination_method", label: "Method" },
    { field: "start_year", label: "Start Year" },
    { field: "start_year_qualifier", label: "Start Qualifier" },
    { field: "start_year_calendar", label: "Start Calendar" },
    { field: "end_year", label: "End Year" },
    { field: "end_year_qualifier", label: "End Qualifier" },
    { field: "end_year_calendar", label: "End Calendar" },
    { field: "information_source", label: "Source" },
    { field: "chronology_remarks", label: "Remarks" },
];
</script>

<template>
    <DetailsSection
        section-title="1. HRIA Discontinued Data"
        :loading="props.loading"
        :visible="true"
    >
        <template #sectionContent>
            <DetailsSection
                section-title="1.1 ADIF Record Information"
                :visible="true"
            >
                <template #sectionContent>
                    <dl v-if="currentData?.unreviewed_adif_record?.aliased_data">
                        <dt v-if="!isEmpty(currentData.unreviewed_adif_record.aliased_data.unreviewed_adif_record)">Unreviewed ADIF Record</dt>
                        <dd v-if="!isEmpty(currentData.unreviewed_adif_record.aliased_data.unreviewed_adif_record)">
                            {{ getDisplayValue(currentData.unreviewed_adif_record.aliased_data.unreviewed_adif_record) }}
                        </dd>

                        <dt v-if="!isEmpty(currentData.unreviewed_adif_record.aliased_data.site_entered_by)">Site Entered By</dt>
                        <dd v-if="!isEmpty(currentData.unreviewed_adif_record.aliased_data.site_entered_by)">
                            {{ getDisplayValue(currentData.unreviewed_adif_record.aliased_data.site_entered_by) }}
                        </dd>

                        <dt v-if="!isEmpty(currentData.unreviewed_adif_record.aliased_data.site_entry_date)">Site Entry Date</dt>
                        <dd v-if="!isEmpty(currentData.unreviewed_adif_record.aliased_data.site_entry_date)">
                            {{ getDisplayValue(currentData.unreviewed_adif_record.aliased_data.site_entry_date) }}
                        </dd>
                    </dl>
                    <div v-else>
                        <p>No ADIF record information available.</p>
                        <p v-if="!currentData">No currentData available</p>
                        <p v-else-if="!currentData.unreviewed_adif_record">No unreviewed_adif_record in currentData</p>
                        <p v-else-if="!currentData.unreviewed_adif_record.aliased_data">No aliased_data in unreviewed_adif_record</p>
                    </div>
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="1.2 Site Dimensions"
                :visible="true"
            >
                <template #sectionContent>
                    <dl v-if="currentData?.site_dimensions?.aliased_data">
                        <dt v-if="!isEmpty(currentData.site_dimensions.aliased_data.length)">Length</dt>
                        <dd v-if="!isEmpty(currentData.site_dimensions.aliased_data.length)">
                            {{ getDisplayValue(currentData.site_dimensions.aliased_data.length) }}
                        </dd>

                        <dt v-if="!isEmpty(currentData.site_dimensions.aliased_data.length_direction)">Length Direction</dt>
                        <dd v-if="!isEmpty(currentData.site_dimensions.aliased_data.length_direction)">
                            {{ getDisplayValue(currentData.site_dimensions.aliased_data.length_direction) }}
                        </dd>

                        <dt v-if="!isEmpty(currentData.site_dimensions.aliased_data.width)">Width</dt>
                        <dd v-if="!isEmpty(currentData.site_dimensions.aliased_data.width)">
                            {{ getDisplayValue(currentData.site_dimensions.aliased_data.width) }}
                        </dd>

                        <dt v-if="!isEmpty(currentData.site_dimensions.aliased_data.width_direction)">Width Direction</dt>
                        <dd v-if="!isEmpty(currentData.site_dimensions.aliased_data.width_direction)">
                            {{ getDisplayValue(currentData.site_dimensions.aliased_data.width_direction) }}
                        </dd>

                        <dt v-if="!isEmpty(currentData.site_dimensions.aliased_data.site_area)">Site Area</dt>
                        <dd v-if="!isEmpty(currentData.site_dimensions.aliased_data.site_area)">
                            {{ getDisplayValue(currentData.site_dimensions.aliased_data.site_area) }}
                        </dd>

                        <dt v-if="!isEmpty(currentData.site_dimensions.aliased_data.boundary_type)">Boundary Type</dt>
                        <dd v-if="!isEmpty(currentData.site_dimensions.aliased_data.boundary_type)">
                            {{ getDisplayValue(currentData.site_dimensions.aliased_data.boundary_type) }}
                        </dd>
                    </dl>
                    <div v-else>
                        <p>No site dimensions information available.</p>
                    </div>
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="1.3 Biogeography"
                :visible="true"
            >
                <template #sectionContent>
                    <dl v-if="currentData?.biogeography?.aliased_data">
                        <dt v-if="!isEmpty(currentData.biogeography.aliased_data.biogeography_type)">Biogeography Type</dt>
                        <dd v-if="!isEmpty(currentData.biogeography.aliased_data.biogeography_type)">
                            {{ getDisplayValue(currentData.biogeography.aliased_data.biogeography_type) }}
                        </dd>

                        <dt v-if="!isEmpty(currentData.biogeography.aliased_data.biogeography_name)">Biogeography Name</dt>
                        <dd v-if="!isEmpty(currentData.biogeography.aliased_data.biogeography_name)">
                            {{ getDisplayValue(currentData.biogeography.aliased_data.biogeography_name) }}
                        </dd>

                        <dt v-if="!isEmpty(currentData.biogeography.aliased_data.biogeography_description)">Biogeography Description</dt>
                        <dd v-if="!isEmpty(currentData.biogeography.aliased_data.biogeography_description)">
                            {{ getDisplayValue(currentData.biogeography.aliased_data.biogeography_description) }}
                        </dd>

                        <dt v-if="!isEmpty(currentData.biogeography.aliased_data.biogeography_entered_by)">Entered By</dt>
                        <dd v-if="!isEmpty(currentData.biogeography.aliased_data.biogeography_entered_by)">
                            {{ getDisplayValue(currentData.biogeography.aliased_data.biogeography_entered_by) }}
                        </dd>

                        <dt v-if="!isEmpty(currentData.biogeography.aliased_data.biogeography_entered_date)">Entered Date</dt>
                        <dd v-if="!isEmpty(currentData.biogeography.aliased_data.biogeography_entered_date)">
                            {{ getDisplayValue(currentData.biogeography.aliased_data.biogeography_entered_date) }}
                        </dd>
                    </dl>
                    <div v-else>
                        <p>No biogeography information available.</p>
                    </div>
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="1.4 HRIA Jurisdiction and Tenure"
                :visible="true"
            >
                <template #sectionContent>
                    <StandardDataTable
                        :table-data="currentData?.hria_jursidiction_and_tenure ?? []"
                        :column-definitions="jurisdictionTenureColumns"
                        title="HRIA Jurisdiction and Tenure"
                        :initial-sort-field-index="4"
                    />
                    <div v-if="!currentData?.hria_jursidiction_and_tenure?.length">
                        <p>No jurisdiction and tenure records available.</p>
                    </div>
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="1.5 Chronology"
                :visible="true"
            >
                <template #sectionContent>
                    <StandardDataTable
                        :table-data="currentData?.chronology ?? []"
                        :column-definitions="chronologyColumns"
                        title="Chronology"
                        :initial-sort-field-index="1"
                    />
                    <div v-if="!currentData?.chronology?.length">
                        <p>No chronology records available.</p>
                    </div>
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="1.6 Archaeological Site"
                :visible="true"
            >
                <template #sectionContent>
                    <dl v-if="currentData?.archaeological_site?.aliased_data">
                        <dt v-if="!isEmpty(currentData.archaeological_site.aliased_data.archaeological_site)">Archaeological Site</dt>
                        <dd v-if="!isEmpty(currentData.archaeological_site.aliased_data.archaeological_site)">
                            {{ getDisplayValue(currentData.archaeological_site.aliased_data.archaeological_site) }}
                        </dd>
                    </dl>
                    <div v-else>
                        <p>No archaeological site information available.</p>
                    </div>
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>
