<script setup lang="ts">
import { computed } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import EmptyState from '@/bcap/components/EmptyState.vue';
import { formatDateTime, getDisplayValue, isEmpty } from '@/bcap/util.ts';
import StandardDataTable from '@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue';
import type {
    BiogeographyTile,
    HriaDiscontinuedDataSchema,
} from '@/bcap/schema/HriaDiscontinuedDataSchema.ts';
import 'primeicons/primeicons.css';

const props = withDefaults(
    defineProps<{
        data: HriaDiscontinuedDataSchema | undefined;
        forceCollapsed?: boolean;
        languageCode?: string;
        loading?: boolean;
    }>(),
    {
        forceCollapsed: undefined,
        languageCode: 'en',
        loading: false,
    },
);

const currentData = computed(() => props.data?.aliased_data);

const jurisdictionTenureColumns = [
    { field: 'site_jurisdiction', label: 'Site Jurisdiction' },
    { field: 'tenure_type', label: 'Tenure Type' },
    { field: 'tenure_identifier', label: 'Tenure Identifier' },
    { field: 'tenure_remarks', label: 'Tenure Remarks', isHtml: true },
    { field: 'jurisdiction_entered_by', label: 'Entered By' },
    { field: 'jurisdiction_entered_date', label: 'Entered Date' },
];

const hriaChronologyColumns = [
    { field: 'determination_method', label: 'Method' },
    { field: 'information_source', label: 'Source' },
    { field: 'chronology_remarks', label: 'Chronology Remarks', isHtml: true },
    { field: 'start_year', label: 'From Date' },
    { field: 'start_year_qualifier', label: 'From Date Qualifier' },
    { field: 'start_year_calendar', label: 'From Date Calendar' },
    { field: 'end_year', label: 'To Date' },
    { field: 'end_year_qualifier', label: 'To Date Qualifier' },
    { field: 'end_year_calendar', label: 'To Date Calendar' },
    { field: 'rcd_unadjusted', label: 'RCD Unadjusted' },
    { field: 'rcd_unadjusted_var', label: 'RCD Unadjusted Var (+/-)' },
    { field: 'rcd_adjusted', label: 'RCD Adjusted' },
    { field: 'rcd_adjusted_var', label: 'RCD Adjusted Var (+/-)' },
    { field: 'rcd_lab_code', label: 'RCD Lab Code' },
    { field: 'rcd_lab_number', label: 'RCD Lab Number' },
    { field: 'chronology_modified_on', label: 'Modified On' },
    { field: 'chronology_modified_by', label: 'Modified By' },
];

const biogeographyColumns = [
    { field: 'biogeography_type', label: 'Biogeography Type' },
    { field: 'biogeography_name', label: 'Biogeography Name' },
    { field: 'biogeography_description', label: 'Biogeography Description' },
    { field: 'biogeography_entered_by', label: 'Entered By' },
    { field: 'biogeography_entered_date', label: 'Entered Date' },
];

const siteDimensionsColumns = [
    { field: 'length', label: 'Length (m)' },
    { field: 'length_direction', label: 'Length Direction' },
    { field: 'width', label: 'Width (m)' },
    { field: 'width_direction', label: 'Width Direction' },
    { field: 'site_area', label: 'Site Area (m²)' },
    { field: 'boundary_type', label: 'Boundary Type' },
    { field: 'dimension_entered_by', label: 'Entered By' },
    { field: 'dimension_entered_date', label: 'Entered Date' },
];

const otherMapsColumns = [
    { field: 'other_maps_map_name', label: 'Map Name' },
    { field: 'other_maps_map_scale', label: 'Map Scale' },
    { field: 'other_maps_modified_on', label: 'Modified On' },
    { field: 'other_maps_modified_by', label: 'Modified By' },
];

const siteBoundaryAnnotationsColumns = [
    { field: 'source_notes', label: 'Source Notes' },
    { field: 'accuracy_remarks', label: 'Accuracy Remarks' },
    { field: 'site_boundary_entered_by', label: 'Entered By' },
    { field: 'site_boundary_entered_on', label: 'Entered On' },
];

const hasAdifRecord = computed(() => {
    const adif = currentData.value?.unreviewed_adif_record?.aliased_data;
    if (!adif) {
        return false;
    }
    return (
        !isEmpty(adif.unreviewed_adif_record) ||
        !isEmpty(adif.site_entered_by) ||
        !isEmpty(adif.site_entry_date)
    );
});

const hasSiteDimensions = computed(() => {
    return !!currentData.value?.site_dimensions;
});

const siteDimensionsTableData = computed(() => {
    const dims = currentData.value?.site_dimensions;
    if (!dims) {
        return [];
    }
    return [dims];
});

const hasBiogeography = computed(() => {
    const bio = currentData.value?.biogeography;

    if (!bio) {
        return false;
    }

    if (Array.isArray(bio)) {
        return bio.length > 0;
    }

    const singleBio = bio as BiogeographyTile;
    const data = singleBio.aliased_data;

    if (!data) {
        return false;
    }

    return (
        !isEmpty(data.biogeography_description) ||
        !isEmpty(data.biogeography_entered_by) ||
        !isEmpty(data.biogeography_entered_date) ||
        !isEmpty(data.biogeography_name) ||
        !isEmpty(data.biogeography_type)
    );
});

const hasJurisdictionTenure = computed(() => {
    const tenure = currentData.value?.hria_jursidiction_and_tenure;
    return tenure && tenure.length > 0;
});

const hasChronology = computed(() => {
    const chrono = currentData.value?.chronology;
    return chrono && chrono.length > 0;
});

const hasArchaeologicalSite = computed(() => {
    const site = currentData.value?.archaeological_site?.aliased_data;
    if (!site) {
        return false;
    }
    return !isEmpty(site.archaeological_site);
});

const hasOtherMaps = computed(() => {
    const maps = currentData.value?.other_maps;
    return maps && maps.length > 0;
});

const hasSiteBoundaryAnnotations = computed(() => {
    const annotations = currentData.value?.site_boundary_annotations;
    return annotations && annotations.length > 0;
});

const chronologyTableData = computed(() => currentData.value?.chronology ?? []);

const jurisdictionTenureTableData = computed(
    () => currentData.value?.hria_jursidiction_and_tenure ?? [],
);

const otherMapsTableData = computed(() => currentData.value?.other_maps ?? []);

const siteBoundaryAnnotationsTableData = computed(
    () => currentData.value?.site_boundary_annotations ?? [],
);

const biogeographyTableData = computed(() => {
    const bio = currentData.value?.biogeography;
    if (!bio) {
        return [];
    }
    if (Array.isArray(bio)) {
        return bio;
    }
    return [bio];
});
</script>

<template>
    <DetailsSection
        section-title="1. HRIA Discontinued Data"
        :force-collapsed="props.forceCollapsed"
        :loading="props.loading"
        :visible="true"
    >
        <template #sectionContent>
            <DetailsSection
                section-title="ADIF Record Information"
                variant="subsection"
                :class="{ 'empty-section': !hasAdifRecord }"
                :visible="true"
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
                                ) === 'true'
                                    ? 'Yes'
                                    : 'No'
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
                                formatDateTime(
                                    getDisplayValue(
                                        currentData?.unreviewed_adif_record
                                            ?.aliased_data?.site_entry_date,
                                    ),
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
                section-title="Archaeological Site"
                variant="subsection"
                :class="{ 'empty-section': !hasArchaeologicalSite }"
                :visible="true"
            >
                <template #sectionContent>
                    <dl v-if="hasArchaeologicalSite">
                        <dt>Archaeological Site</dt>
                        <dd>
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

            <DetailsSection
                section-title="Biogeography"
                variant="subsection"
                :class="{ 'empty-section': !hasBiogeography }"
                :visible="true"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasBiogeography"
                        :column-definitions="biogeographyColumns"
                        :initial-sort-field-index="0"
                        :table-data="biogeographyTableData"
                    />
                    <EmptyState
                        v-else
                        message="No biogeography information available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Site Dimensions"
                variant="subsection"
                :class="{ 'empty-section': !hasSiteDimensions }"
                :visible="true"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasSiteDimensions"
                        :column-definitions="siteDimensionsColumns"
                        :initial-sort-field-index="0"
                        :table-data="siteDimensionsTableData"
                    />
                    <EmptyState
                        v-else
                        message="No site dimensions information available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Jurisdiction and Tenure"
                variant="subsection"
                :class="{ 'empty-section': !hasJurisdictionTenure }"
                :visible="true"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasJurisdictionTenure"
                        :column-definitions="jurisdictionTenureColumns"
                        :initial-sort-field-index="0"
                        :table-data="jurisdictionTenureTableData"
                    />
                    <EmptyState
                        v-else
                        message="No jurisdiction and tenure information available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Chronology (Radiocarbon)"
                variant="subsection"
                :class="{ 'empty-section': !hasChronology }"
                :visible="true"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasChronology"
                        :column-definitions="hriaChronologyColumns"
                        :initial-sort-field-index="0"
                        :table-data="chronologyTableData"
                    />
                    <EmptyState
                        v-else
                        message="No chronology information available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Site Boundary Annotations"
                variant="subsection"
                :class="{ 'empty-section': !hasSiteBoundaryAnnotations }"
                :visible="true"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasSiteBoundaryAnnotations"
                        :column-definitions="siteBoundaryAnnotationsColumns"
                        :initial-sort-field-index="0"
                        :table-data="siteBoundaryAnnotationsTableData"
                    />
                    <EmptyState
                        v-else
                        message="No site boundary annotations available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Other Maps"
                variant="subsection"
                :class="{ 'empty-section': !hasOtherMaps }"
                :visible="true"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasOtherMaps"
                        :column-definitions="otherMapsColumns"
                        :initial-sort-field-index="0"
                        :table-data="otherMapsTableData"
                    />
                    <EmptyState
                        v-else
                        message="No other maps information available."
                    />
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>

<style scoped>
.empty-state {
    color: #6c757d;
    font-style: italic;
    padding: 1rem;
    text-align: center;
}
</style>
