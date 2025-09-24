<script setup lang="ts">
import { computed } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import EmptyState from '@/bcap/components/EmptyState.vue';
import { getDisplayValue, isEmpty } from '@/bcap/util.ts';
import StandardDataTable from '@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue';
import 'primeicons/primeicons.css';
import type { AliasedNodeData } from '@/arches_component_lab/types.ts';

const props = withDefaults(
    defineProps<{
        data: any;
        siteVisitData: any[];
        hriaData: any;
        loading?: boolean;
        languageCode?: string;
        forceCollapsed?: boolean;
    }>(),
    {
        languageCode: 'en',
    },
);

const locationAndAccess = computed(() => {
    if (!props.siteVisitData?.length) return [];

    return props.siteVisitData
        .map((visit) => ({
            location:
                visit.aliased_data?.site_visit_location?.aliased_data
                    ?.location_and_access,
            visitName: visit.descriptors?.en?.name,
        }))
        .filter(
            (item) =>
                item.location && !isEmpty(item.location as AliasedNodeData),
        );
});

const biogeographyColumns = [
    { field: 'biogeography_type', label: 'Type' },
    { field: 'biogeography_name', label: 'Name' },
    { field: 'biogeography_description', label: 'Description' },
];

const tenureColumns = [
    { field: 'tenure_type', label: 'Tenure Type' },
    { field: 'tenure_description', label: 'Tenure Description' },
];

const discontinuedTenureColumns = [
    { field: 'jurisdiction', label: 'Jurisdiction' },
    { field: 'tenure_reserves_type', label: 'Tenure/Reserves Type' },
    { field: 'description', label: 'Description' },
    { field: 'tenure_remarks', label: 'Tenure Remarks' },
    { field: 'modified_on', label: 'Modified On' },
    { field: 'modified_by', label: 'Modified By' },
];

const tenureRemarksColumns = [
    { field: 'tenure_remarks', label: 'Tenure Remarks' },
    { field: 'entered_on', label: 'Entered On' },
    { field: 'entered_by', label: 'Entered By' },
];

const discontinuedAddressColumns = [
    { field: 'street_number', label: 'Street Number' },
    { field: 'street_name', label: 'Street Name' },
    { field: 'city', label: 'City' },
    { field: 'postal_code', label: 'Postal Code' },
    { field: 'pid', label: 'PID' },
    { field: 'pin', label: 'PIN' },
    { field: 'legal_type', label: 'Legal Type' },
    { field: 'legal_number', label: 'Legal Number' },
    { field: 'legal_description', label: 'Legal Description' },
    { field: 'modified_on', label: 'Modified On' },
    { field: 'modified_by', label: 'Modified By' },
];

const hasCoordinates = computed(() => {
    return props.data?.coordinates?.aliased_data;
});

const hasTenureAndReserves = computed(() => {
    return (
        props.data?.tenure_and_reserves &&
        props.data.tenure_and_reserves.length > 0
    );
});

const hasTenureRemarks = computed(() => {
    return (
        props.data?.tenure_remarks &&
        Array.isArray(props.data.tenure_remarks) &&
        props.data.tenure_remarks.length > 0
    );
});

const hasDiscontinuedTenure = computed(() => {
    return (
        props.hriaData?.aliased_data?.hria_jursidiction_and_tenure &&
        props.hriaData.aliased_data.hria_jursidiction_and_tenure.length > 0
    );
});

const hasLocationAndAccess = computed(() => {
    return locationAndAccess.value.length > 0;
});

const hasBcPropertyAddress = computed(() => {
    return props.data?.bc_property_address?.[0]?.aliased_data;
});

const hasBcPropertyLegalDescription = computed(() => {
    return props.data?.bc_property_address?.[0]?.aliased_data
        ?.bc_property_legal_description?.[0]?.aliased_data;
});

const hasAddressRemarks = computed(() => {
    return props.data?.address_remarks?.aliased_data;
});

const hasDiscontinuedAddress = computed(() => {
    return (
        props.hriaData?.aliased_data?.discontinued_address_attributes &&
        props.hriaData.aliased_data.discontinued_address_attributes.length > 0
    );
});

const hasAddressInfo = computed(() => {
    return (
        hasBcPropertyAddress.value ||
        hasBcPropertyLegalDescription.value ||
        hasAddressRemarks.value ||
        hasDiscontinuedAddress.value
    );
});

const hasGisElevation = computed(() => {
    return (
        props.data?.elevation?.aliased_data &&
        (!isEmpty(props.data.elevation.aliased_data.gis_lower_elevation) ||
            !isEmpty(props.data.elevation.aliased_data.gis_upper_elevation))
    );
});

const hasElevationComments = computed(() => {
    return props.data?.elevation?.aliased_data?.elevation_comments?.length > 0;
});

const hasElevation = computed(() => {
    return hasGisElevation.value || hasElevationComments.value;
});

const hasBiogeography = computed(() => {
    return props.data?.biogeography && props.data.biogeography.length > 0;
});
</script>

<template>
    <DetailsSection
        section-title="4. Location"
        :loading="props.loading"
        :visible="true"
        :force-collapsed="props.forceCollapsed"
    >
        <template #sectionContent>
            <DetailsSection
                section-title="Coordinates (GIS)"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasCoordinates }"
            >
                <template #sectionContent>
                    <dl v-if="hasCoordinates">
                        <dt
                            v-if="
                                !isEmpty(
                                    props.data.coordinates.aliased_data
                                        .utm_zone,
                                )
                            "
                        >
                            UTM Zone
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    props.data.coordinates.aliased_data
                                        .utm_zone,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    props.data.coordinates.aliased_data
                                        .utm_zone,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    props.data.coordinates.aliased_data
                                        .utm_easting,
                                )
                            "
                        >
                            UTM Easting
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    props.data.coordinates.aliased_data
                                        .utm_easting,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    props.data.coordinates.aliased_data
                                        .utm_easting,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    props.data.coordinates.aliased_data
                                        .utm_northing,
                                )
                            "
                        >
                            UTM Northing
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    props.data.coordinates.aliased_data
                                        .utm_northing,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    props.data.coordinates.aliased_data
                                        .utm_northing,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    props.data.coordinates.aliased_data
                                        .latitude,
                                )
                            "
                        >
                            Latitude
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    props.data.coordinates.aliased_data
                                        .latitude,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    props.data.coordinates.aliased_data
                                        .latitude,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    props.data.coordinates.aliased_data
                                        .longitude,
                                )
                            "
                        >
                            Longitude
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    props.data.coordinates.aliased_data
                                        .longitude,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    props.data.coordinates.aliased_data
                                        .longitude,
                                )
                            }}
                        </dd>
                    </dl>
                    <EmptyState
                        v-else
                        message="No coordinate information available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Tenure and Reserves"
                variant="subsection"
                :visible="true"
            >
                <template #sectionContent>
                    <DetailsSection
                        section-title="Auto-populated Tenure and Reserves"
                        variant="subsection"
                        :visible="true"
                        :class="{ 'empty-section': !hasTenureAndReserves }"
                    >
                        <template #sectionContent>
                            <StandardDataTable
                                v-if="hasTenureAndReserves"
                                :table-data="
                                    props.data?.tenure_and_reserves ?? []
                                "
                                :column-definitions="tenureColumns"
                                :initial-sort-field-index="0"
                            />
                            <EmptyState
                                v-else
                                message="No auto-populated tenure and reserves information available."
                            />
                        </template>
                    </DetailsSection>

                    <DetailsSection
                        section-title="Tenure Remarks"
                        variant="subsection"
                        :visible="true"
                        :class="{ 'empty-section': !hasTenureRemarks }"
                    >
                        <template #sectionContent>
                            <StandardDataTable
                                v-if="hasTenureRemarks"
                                :table-data="props.data?.tenure_remarks ?? []"
                                :column-definitions="tenureRemarksColumns"
                                :initial-sort-field-index="1"
                            />
                            <EmptyState
                                v-else
                                message="No tenure remarks available."
                            />
                        </template>
                    </DetailsSection>

                    <DetailsSection
                        section-title="Discontinued Attributes"
                        variant="subsection"
                        :visible="true"
                        :class="{ 'empty-section': !hasDiscontinuedTenure }"
                    >
                        <template #sectionContent>
                            <StandardDataTable
                                v-if="hasDiscontinuedTenure"
                                :table-data="
                                    props.hriaData?.aliased_data
                                        ?.hria_jursidiction_and_tenure ?? []
                                "
                                :column-definitions="discontinuedTenureColumns"
                                :initial-sort-field-index="4"
                            />
                            <EmptyState
                                v-else
                                message="No discontinued tenure attributes available."
                            />
                        </template>
                    </DetailsSection>
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Location and Access"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasLocationAndAccess }"
            >
                <template #sectionContent>
                    <dl v-if="hasLocationAndAccess">
                        <template
                            v-for="(item, index) in locationAndAccess"
                            :key="index"
                        >
                            <dt>
                                {{ item.visitName || `Visit ${index + 1}` }} -
                                Location and Access
                            </dt>
                            <dd>
                                {{
                                    getDisplayValue(
                                        item.location as AliasedNodeData,
                                    )
                                }}
                            </dd>
                        </template>
                    </dl>
                    <EmptyState
                        v-else
                        message="No location and access information available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Address and Legal Description"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasAddressInfo }"
            >
                <template #sectionContent>
                    <div v-if="hasAddressInfo">
                        <DetailsSection
                            section-title="Street Address"
                            variant="subsection"
                            :visible="true"
                            :class="{ 'empty-section': !hasBcPropertyAddress }"
                        >
                            <template #sectionContent>
                                <dl v-if="hasBcPropertyAddress">
                                    <dt
                                        v-if="
                                            !isEmpty(
                                                props.data
                                                    .bc_property_address[0]
                                                    .aliased_data.street_number,
                                            )
                                        "
                                    >
                                        Street Number
                                    </dt>
                                    <dd
                                        v-if="
                                            !isEmpty(
                                                props.data
                                                    .bc_property_address[0]
                                                    .aliased_data.street_number,
                                            )
                                        "
                                    >
                                        {{
                                            getDisplayValue(
                                                props.data
                                                    .bc_property_address[0]
                                                    .aliased_data.street_number,
                                            )
                                        }}
                                    </dd>

                                    <dt
                                        v-if="
                                            !isEmpty(
                                                props.data
                                                    .bc_property_address[0]
                                                    .aliased_data.street_name,
                                            )
                                        "
                                    >
                                        Street Name
                                    </dt>
                                    <dd
                                        v-if="
                                            !isEmpty(
                                                props.data
                                                    .bc_property_address[0]
                                                    .aliased_data.street_name,
                                            )
                                        "
                                    >
                                        {{
                                            getDisplayValue(
                                                props.data
                                                    .bc_property_address[0]
                                                    .aliased_data.street_name,
                                            )
                                        }}
                                    </dd>

                                    <dt
                                        v-if="
                                            !isEmpty(
                                                props.data
                                                    .bc_property_address[0]
                                                    .aliased_data.city,
                                            )
                                        "
                                    >
                                        City
                                    </dt>
                                    <dd
                                        v-if="
                                            !isEmpty(
                                                props.data
                                                    .bc_property_address[0]
                                                    .aliased_data.city,
                                            )
                                        "
                                    >
                                        {{
                                            getDisplayValue(
                                                props.data
                                                    .bc_property_address[0]
                                                    .aliased_data.city,
                                            )
                                        }}
                                    </dd>

                                    <dt
                                        v-if="
                                            !isEmpty(
                                                props.data
                                                    .bc_property_address[0]
                                                    .aliased_data.postal_code,
                                            )
                                        "
                                    >
                                        Postal Code
                                    </dt>
                                    <dd
                                        v-if="
                                            !isEmpty(
                                                props.data
                                                    .bc_property_address[0]
                                                    .aliased_data.postal_code,
                                            )
                                        "
                                    >
                                        {{
                                            getDisplayValue(
                                                props.data
                                                    .bc_property_address[0]
                                                    .aliased_data.postal_code,
                                            )
                                        }}
                                    </dd>
                                </dl>
                                <EmptyState
                                    v-else
                                    message="No street address information available."
                                />
                            </template>
                        </DetailsSection>

                        <DetailsSection
                            section-title="Legal Description"
                            variant="subsection"
                            :visible="true"
                            :class="{
                                'empty-section': !hasBcPropertyLegalDescription,
                            }"
                        >
                            <template #sectionContent>
                                <dl v-if="hasBcPropertyLegalDescription">
                                    <dt
                                        v-if="
                                            !isEmpty(
                                                props.data
                                                    .bc_property_address[0]
                                                    .aliased_data
                                                    .bc_property_legal_description[0]
                                                    .aliased_data.pid,
                                            )
                                        "
                                    >
                                        PID
                                    </dt>
                                    <dd
                                        v-if="
                                            !isEmpty(
                                                props.data
                                                    .bc_property_address[0]
                                                    .aliased_data
                                                    .bc_property_legal_description[0]
                                                    .aliased_data.pid,
                                            )
                                        "
                                    >
                                        {{
                                            getDisplayValue(
                                                props.data
                                                    .bc_property_address[0]
                                                    .aliased_data
                                                    .bc_property_legal_description[0]
                                                    .aliased_data.pid,
                                            )
                                        }}
                                    </dd>

                                    <dt
                                        v-if="
                                            !isEmpty(
                                                props.data
                                                    .bc_property_address[0]
                                                    .aliased_data
                                                    .bc_property_legal_description[0]
                                                    .aliased_data.pin,
                                            )
                                        "
                                    >
                                        PIN
                                    </dt>
                                    <dd
                                        v-if="
                                            !isEmpty(
                                                props.data
                                                    .bc_property_address[0]
                                                    .aliased_data
                                                    .bc_property_legal_description[0]
                                                    .aliased_data.pin,
                                            )
                                        "
                                    >
                                        {{
                                            getDisplayValue(
                                                props.data
                                                    .bc_property_address[0]
                                                    .aliased_data
                                                    .bc_property_legal_description[0]
                                                    .aliased_data.pin,
                                            )
                                        }}
                                    </dd>

                                    <dt
                                        v-if="
                                            !isEmpty(
                                                props.data
                                                    .bc_property_address[0]
                                                    .aliased_data
                                                    .bc_property_legal_description[0]
                                                    .aliased_data
                                                    .legal_description,
                                            )
                                        "
                                    >
                                        Legal Description
                                    </dt>
                                    <dd
                                        v-if="
                                            !isEmpty(
                                                props.data
                                                    .bc_property_address[0]
                                                    .aliased_data
                                                    .bc_property_legal_description[0]
                                                    .aliased_data
                                                    .legal_description,
                                            )
                                        "
                                    >
                                        {{
                                            getDisplayValue(
                                                props.data
                                                    .bc_property_address[0]
                                                    .aliased_data
                                                    .bc_property_legal_description[0]
                                                    .aliased_data
                                                    .legal_description,
                                            )
                                        }}
                                    </dd>
                                </dl>
                                <EmptyState
                                    v-else
                                    message="No legal description information available."
                                />
                            </template>
                        </DetailsSection>

                        <DetailsSection
                            section-title="Address and Legal Description Remarks"
                            variant="subsection"
                            :visible="true"
                            :class="{ 'empty-section': !hasAddressRemarks }"
                        >
                            <template #sectionContent>
                                <dl v-if="hasAddressRemarks">
                                    <dt
                                        v-if="
                                            !isEmpty(
                                                props.data.address_remarks
                                                    .aliased_data
                                                    .address_and_legal_description_remarks,
                                            )
                                        "
                                    >
                                        Address and Legal Description Remarks
                                    </dt>
                                    <dd
                                        v-if="
                                            !isEmpty(
                                                props.data.address_remarks
                                                    .aliased_data
                                                    .address_and_legal_description_remarks,
                                            )
                                        "
                                    >
                                        {{
                                            getDisplayValue(
                                                props.data.address_remarks
                                                    .aliased_data
                                                    .address_and_legal_description_remarks,
                                            )
                                        }}
                                    </dd>

                                    <dt
                                        v-if="
                                            !isEmpty(
                                                props.data.address_remarks
                                                    .aliased_data.entered_on,
                                            )
                                        "
                                    >
                                        Entered On
                                    </dt>
                                    <dd
                                        v-if="
                                            !isEmpty(
                                                props.data.address_remarks
                                                    .aliased_data.entered_on,
                                            )
                                        "
                                    >
                                        {{
                                            getDisplayValue(
                                                props.data.address_remarks
                                                    .aliased_data.entered_on,
                                            )
                                        }}
                                    </dd>

                                    <dt
                                        v-if="
                                            !isEmpty(
                                                props.data.address_remarks
                                                    .aliased_data.entered_by,
                                            )
                                        "
                                    >
                                        Entered By
                                    </dt>
                                    <dd
                                        v-if="
                                            !isEmpty(
                                                props.data.address_remarks
                                                    .aliased_data.entered_by,
                                            )
                                        "
                                    >
                                        {{
                                            getDisplayValue(
                                                props.data.address_remarks
                                                    .aliased_data.entered_by,
                                            )
                                        }}
                                    </dd>
                                </dl>
                                <EmptyState
                                    v-else
                                    message="No address remarks available."
                                />
                            </template>
                        </DetailsSection>

                        <DetailsSection
                            section-title="Discontinued Address Attributes"
                            variant="subsection"
                            :visible="true"
                            :class="{
                                'empty-section': !hasDiscontinuedAddress,
                            }"
                        >
                            <template #sectionContent>
                                <StandardDataTable
                                    v-if="hasDiscontinuedAddress"
                                    :table-data="
                                        props.hriaData?.aliased_data
                                            ?.discontinued_address_attributes ??
                                        []
                                    "
                                    :column-definitions="
                                        discontinuedAddressColumns
                                    "
                                    :initial-sort-field-index="9"
                                />
                                <EmptyState
                                    v-else
                                    message="No discontinued address attributes available."
                                />
                            </template>
                        </DetailsSection>
                    </div>
                    <EmptyState
                        v-else
                        message="No address and legal description information available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Elevation"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasElevation }"
            >
                <template #sectionContent>
                    <div v-if="hasElevation">
                        <DetailsSection
                            section-title="GIS Elevation"
                            variant="subsection"
                            :visible="true"
                            :class="{ 'empty-section': !hasGisElevation }"
                        >
                            <template #sectionContent>
                                <dl v-if="hasGisElevation">
                                    <dt
                                        v-if="
                                            !isEmpty(
                                                props.data.elevation
                                                    .aliased_data
                                                    .gis_lower_elevation,
                                            )
                                        "
                                    >
                                        Lower (m asl)
                                    </dt>
                                    <dd
                                        v-if="
                                            !isEmpty(
                                                props.data.elevation
                                                    .aliased_data
                                                    .gis_lower_elevation,
                                            )
                                        "
                                    >
                                        {{
                                            getDisplayValue(
                                                props.data.elevation
                                                    .aliased_data
                                                    .gis_lower_elevation,
                                            )
                                        }}
                                    </dd>

                                    <dt
                                        v-if="
                                            !isEmpty(
                                                props.data.elevation
                                                    .aliased_data
                                                    .gis_upper_elevation,
                                            )
                                        "
                                    >
                                        Upper (m asl)
                                    </dt>
                                    <dd
                                        v-if="
                                            !isEmpty(
                                                props.data.elevation
                                                    .aliased_data
                                                    .gis_upper_elevation,
                                            )
                                        "
                                    >
                                        {{
                                            getDisplayValue(
                                                props.data.elevation
                                                    .aliased_data
                                                    .gis_upper_elevation,
                                            )
                                        }}
                                    </dd>
                                </dl>
                                <EmptyState
                                    v-else
                                    message="No GIS elevation information available."
                                />
                            </template>
                        </DetailsSection>

                        <DetailsSection
                            section-title="Elevation Remarks"
                            variant="subsection"
                            :visible="true"
                            :class="{ 'empty-section': !hasElevationComments }"
                        >
                            <template #sectionContent>
                                <dl v-if="hasElevationComments">
                                    <template
                                        v-for="(comment, index) in props.data
                                            .elevation.aliased_data
                                            .elevation_comments"
                                        :key="index"
                                    >
                                        <dt>
                                            Elevation Remarks {{ index + 1 }}
                                        </dt>
                                        <dd
                                            v-html="
                                                getDisplayValue(
                                                    comment.aliased_data
                                                        ?.elevation_comments,
                                                )
                                            "
                                        ></dd>
                                    </template>
                                </dl>
                                <EmptyState
                                    v-else
                                    message="No elevation remarks available."
                                />
                            </template>
                        </DetailsSection>
                    </div>
                    <EmptyState
                        v-else
                        message="No elevation information available."
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
                    <StandardDataTable
                        v-if="hasBiogeography"
                        :table-data="props.data?.biogeography ?? []"
                        :column-definitions="biogeographyColumns"
                        :initial-sort-field-index="0"
                    />
                    <EmptyState
                        v-else
                        message="No biogeography information available."
                    />
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>
