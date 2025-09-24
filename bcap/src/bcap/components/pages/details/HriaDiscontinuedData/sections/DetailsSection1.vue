<script setup lang="ts">
import { computed } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import EmptyState from '@/bcap/components/EmptyState.vue';
import { getDisplayValue, isEmpty } from '@/bcap/util.ts';
import StandardDataTable from '@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue';
import type { HriaDiscontinuedDataSchema } from '@/bcap/schema/HriaDiscontinuedDataSchema.ts';
import type { AliasedNodeData } from '@/arches_component_lab/types.ts';
import 'primeicons/primeicons.css';

const props = withDefaults(
    defineProps<{
        data: HriaDiscontinuedDataSchema | undefined;
        loading?: boolean;
        languageCode?: string;
    }>(),
    {
        languageCode: 'en',
    },
);

const currentData = computed(() => {
    return props.data?.aliased_data;
});

const jurisdictionTenureColumns = [
    { field: 'site_jurisdiction', label: 'Site Jurisdiction' },
    { field: 'tenure_type', label: 'Tenure Type' },
    { field: 'tenure_identifier', label: 'Tenure Identifier' },
    { field: 'tenure_remarks', label: 'Tenure Remarks' },
    { field: 'jurisdiction_entered_date', label: 'Entered Date' },
    { field: 'jurisdiction_entered_by', label: 'Entered By' },
];

const chronologyColumns = [
    { field: 'determination_method', label: 'Method' },
    { field: 'start_year', label: 'Start Year' },
    { field: 'start_year_qualifier', label: 'Start Qualifier' },
    { field: 'start_year_calendar', label: 'Start Calendar' },
    { field: 'end_year', label: 'End Year' },
    { field: 'end_year_qualifier', label: 'End Qualifier' },
    { field: 'end_year_calendar', label: 'End Calendar' },
    { field: 'information_source', label: 'Source' },
    { field: 'chronology_remarks', label: 'Remarks' },
];

const hasAdifRecord = computed(() => {
    return currentData.value?.unreviewed_adif_record?.aliased_data;
});

const hasSiteDimensions = computed(() => {
    return currentData.value?.site_dimensions?.aliased_data;
});

const hasBiogeography = computed(() => {
    return currentData.value?.biogeography?.aliased_data;
});

const hasJurisdictionTenure = computed(() => {
    return (
        currentData.value?.hria_jursidiction_and_tenure &&
        currentData.value.hria_jursidiction_and_tenure.length > 0
    );
});

const hasChronology = computed(() => {
    return (
        currentData.value?.chronology && currentData.value.chronology.length > 0
    );
});

const hasArchaeologicalSite = computed(() => {
    return currentData.value?.archaeological_site?.aliased_data;
});
</script>

<template>
    <DetailsSection
        section-title="1. HRIA Discontinued Data"
        :loading="props.loading"
        :visible="true"
    >
        <template #sectionContent>
            <DetailsSection
                section-title="ADIF Record Information"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasAdifRecord }"
            >
                <template #sectionContent>
                    <dl v-if="hasAdifRecord">
                        <dt
                            v-if="
                                !isEmpty(
                                    currentData?.unreviewed_adif_record
                                        ?.aliased_data?.unreviewed_adif_record,
                                )
                            "
                        >
                            Unreviewed ADIF Record
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    currentData?.unreviewed_adif_record
                                        ?.aliased_data?.unreviewed_adif_record,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    currentData?.unreviewed_adif_record
                                        ?.aliased_data?.unreviewed_adif_record,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    currentData?.unreviewed_adif_record
                                        ?.aliased_data?.site_entered_by,
                                )
                            "
                        >
                            Site Entered By
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    currentData?.unreviewed_adif_record
                                        ?.aliased_data?.site_entered_by,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    currentData?.unreviewed_adif_record
                                        ?.aliased_data?.site_entered_by,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    currentData?.unreviewed_adif_record
                                        ?.aliased_data?.site_entry_date,
                                )
                            "
                        >
                            Site Entry Date
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    currentData?.unreviewed_adif_record
                                        ?.aliased_data?.site_entry_date,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    currentData?.unreviewed_adif_record
                                        ?.aliased_data?.site_entry_date,
                                )
                            }}
                        </dd>
                    </dl>
                    <EmptyState
                        v-else
                        message="No ADIF record information available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Site Dimensions"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasSiteDimensions }"
            >
                <template #sectionContent>
                    <dl v-if="hasSiteDimensions">
                        <dt
                            v-if="
                                !isEmpty(
                                    currentData?.site_dimensions?.aliased_data
                                        ?.length,
                                )
                            "
                        >
                            Length
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    currentData?.site_dimensions?.aliased_data
                                        ?.length,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    currentData?.site_dimensions?.aliased_data
                                        ?.length,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    currentData?.site_dimensions?.aliased_data
                                        ?.length_direction,
                                )
                            "
                        >
                            Length Direction
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    currentData?.site_dimensions?.aliased_data
                                        ?.length_direction,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    currentData?.site_dimensions?.aliased_data
                                        ?.length_direction,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    currentData?.site_dimensions?.aliased_data
                                        ?.width,
                                )
                            "
                        >
                            Width
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    currentData?.site_dimensions?.aliased_data
                                        ?.width,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    currentData?.site_dimensions?.aliased_data
                                        ?.width,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    currentData?.site_dimensions?.aliased_data
                                        ?.width_direction,
                                )
                            "
                        >
                            Width Direction
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    currentData?.site_dimensions?.aliased_data
                                        ?.width_direction,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    currentData?.site_dimensions?.aliased_data
                                        ?.width_direction,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    currentData?.site_dimensions?.aliased_data
                                        ?.site_area,
                                )
                            "
                        >
                            Site Area
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    currentData?.site_dimensions?.aliased_data
                                        ?.site_area,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    currentData?.site_dimensions?.aliased_data
                                        ?.site_area,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    currentData?.site_dimensions?.aliased_data
                                        ?.boundary_type,
                                )
                            "
                        >
                            Boundary Type
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    currentData?.site_dimensions?.aliased_data
                                        ?.boundary_type,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    currentData?.site_dimensions?.aliased_data
                                        ?.boundary_type,
                                )
                            }}
                        </dd>
                    </dl>
                    <EmptyState
                        v-else
                        message="No site dimensions information available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Biogeography"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasBiogeography }"
            >
                <template #sectionContent>
                    <dl v-if="hasBiogeography">
                        <dt
                            v-if="
                                !isEmpty(
                                    currentData?.biogeography?.aliased_data
                                        ?.biogeography_type,
                                )
                            "
                        >
                            Biogeography Type
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    currentData?.biogeography?.aliased_data
                                        ?.biogeography_type,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    currentData?.biogeography?.aliased_data
                                        ?.biogeography_type,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    currentData?.biogeography?.aliased_data
                                        ?.biogeography_name,
                                )
                            "
                        >
                            Biogeography Name
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    currentData?.biogeography?.aliased_data
                                        ?.biogeography_name,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    currentData?.biogeography?.aliased_data
                                        ?.biogeography_name,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    currentData?.biogeography?.aliased_data
                                        ?.biogeography_description,
                                )
                            "
                        >
                            Biogeography Description
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    currentData?.biogeography?.aliased_data
                                        ?.biogeography_description,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    currentData?.biogeography?.aliased_data
                                        ?.biogeography_description,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    currentData?.biogeography?.aliased_data
                                        ?.biogeography_entered_by,
                                )
                            "
                        >
                            Entered By
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    currentData?.biogeography?.aliased_data
                                        ?.biogeography_entered_by,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    currentData?.biogeography?.aliased_data
                                        ?.biogeography_entered_by,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    currentData?.biogeography?.aliased_data
                                        ?.biogeography_entered_date,
                                )
                            "
                        >
                            Entered Date
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    currentData?.biogeography?.aliased_data
                                        ?.biogeography_entered_date,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    currentData?.biogeography?.aliased_data
                                        ?.biogeography_entered_date,
                                )
                            }}
                        </dd>
                    </dl>
                    <EmptyState
                        v-else
                        message="No biogeography information available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="HRIA Jurisdiction and Tenure"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasJurisdictionTenure }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasJurisdictionTenure"
                        :table-data="
                            currentData?.hria_jursidiction_and_tenure ?? []
                        "
                        :column-definitions="jurisdictionTenureColumns"
                        :initial-sort-field-index="4"
                    />
                    <EmptyState
                        v-else
                        message="No jurisdiction and tenure records available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Chronology"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasChronology }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasChronology"
                        :table-data="currentData?.chronology ?? []"
                        :column-definitions="chronologyColumns"
                        :initial-sort-field-index="1"
                    />
                    <EmptyState
                        v-else
                        message="No chronology records available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Archaeological Site"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasArchaeologicalSite }"
            >
                <template #sectionContent>
                    <dl v-if="hasArchaeologicalSite">
                        <dt
                            v-if="
                                !isEmpty(
                                    currentData?.archaeological_site
                                        ?.aliased_data?.archaeological_site,
                                )
                            "
                        >
                            Archaeological Site
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    currentData?.archaeological_site
                                        ?.aliased_data?.archaeological_site,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    currentData?.archaeological_site
                                        ?.aliased_data?.archaeological_site,
                                )
                            }}
                        </dd>
                    </dl>
                    <EmptyState
                        v-else
                        message="No archaeological site information available."
                    />
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>
