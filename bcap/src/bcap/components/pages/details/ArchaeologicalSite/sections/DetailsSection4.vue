<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";
import { getDisplayValue, isEmpty } from "@/bcap/util.ts";
import StandardDataTable from "@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue";
import "primeicons/primeicons.css";
import type { AliasedNodeData } from "@/arches_component_lab/types.ts";

const props = withDefaults(
    defineProps<{
        data: any;
        siteVisitData: any[];
        loading?: boolean;
        languageCode?: string;
    }>(),
    {
        languageCode: "en",
    },
);

const locationAndAccess = computed(() => {
    if (!props.siteVisitData?.length) return [];

    return props.siteVisitData
        .map(visit => ({
            location: visit.aliased_data?.site_visit_location?.aliased_data?.location_and_access,
            visitName: visit.descriptors?.en?.name
        }))
        .filter(item => item.location && !isEmpty(item.location as AliasedNodeData));
});

const biogeographyColumns = [
    { field: "biogeography_type", label: "Type" },
    { field: "biogeography_name", label: "Name" },
    { field: "biogeography_description", label: "Description" },
];

const tenureColumns = [
    { field: "tenure_type", label: "Tenure Type" },
    { field: "tenure_description", label: "Description" },
];
</script>

<template>
    <DetailsSection
        section-title="4. Location"
        :loading="props.loading"
        :visible="true"
    >
        <template #sectionContent>
            <DetailsSection
                section-title="4.1 Coordinates (GIS)"
                :visible="true"
            >
                <template #sectionContent>
                    <dl v-if="props.data?.coordinates?.aliased_data">
                        <dt v-if="!isEmpty(props.data.coordinates.aliased_data.utm_zone)">UTM Zone</dt>
                        <dd v-if="!isEmpty(props.data.coordinates.aliased_data.utm_zone)">
                            {{ getDisplayValue(props.data.coordinates.aliased_data.utm_zone) }}
                        </dd>

                        <dt v-if="!isEmpty(props.data.coordinates.aliased_data.utm_easting)">UTM Easting</dt>
                        <dd v-if="!isEmpty(props.data.coordinates.aliased_data.utm_easting)">
                            {{ getDisplayValue(props.data.coordinates.aliased_data.utm_easting) }}
                        </dd>

                        <dt v-if="!isEmpty(props.data.coordinates.aliased_data.utm_northing)">UTM Northing</dt>
                        <dd v-if="!isEmpty(props.data.coordinates.aliased_data.utm_northing)">
                            {{ getDisplayValue(props.data.coordinates.aliased_data.utm_northing) }}
                        </dd>

                        <dt v-if="!isEmpty(props.data.coordinates.aliased_data.latitude)">Latitude</dt>
                        <dd v-if="!isEmpty(props.data.coordinates.aliased_data.latitude)">
                            {{ getDisplayValue(props.data.coordinates.aliased_data.latitude) }}
                        </dd>

                        <dt v-if="!isEmpty(props.data.coordinates.aliased_data.longitude)">Longitude</dt>
                        <dd v-if="!isEmpty(props.data.coordinates.aliased_data.longitude)">
                            {{ getDisplayValue(props.data.coordinates.aliased_data.longitude) }}
                        </dd>
                    </dl>
                    <div v-else>
                        <p>No coordinate information available.</p>
                    </div>
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="4.2 Tenure and Reserves"
                :visible="true"
            >
                <template #sectionContent>
                    <StandardDataTable
                        :table-data="props.data?.tenure_and_reserves ?? []"
                        :column-definitions="tenureColumns"
                        title="Tenure and Reserves (Auto-populated from BCGW)"
                        :initial-sort-field-index="0"
                    />
                    <div v-if="!props.data?.tenure_and_reserves?.length">
                        <p>No auto-populated tenure information available.</p>
                    </div>

                    <dl v-if="props.data?.manual_tenure?.aliased_data">
                        <dt v-if="!isEmpty(props.data.manual_tenure.aliased_data.tenure_remarks)">Tenure Remarks</dt>
                        <dd v-if="!isEmpty(props.data.manual_tenure.aliased_data.tenure_remarks)">
                            {{ getDisplayValue(props.data.manual_tenure.aliased_data.tenure_remarks) }}
                        </dd>

                        <dt v-if="!isEmpty(props.data.manual_tenure.aliased_data.entered_on)">Entered On</dt>
                        <dd v-if="!isEmpty(props.data.manual_tenure.aliased_data.entered_on)">
                            {{ getDisplayValue(props.data.manual_tenure.aliased_data.entered_on) }}
                        </dd>

                        <dt v-if="!isEmpty(props.data.manual_tenure.aliased_data.entered_by)">Entered By</dt>
                        <dd v-if="!isEmpty(props.data.manual_tenure.aliased_data.entered_by)">
                            {{ getDisplayValue(props.data.manual_tenure.aliased_data.entered_by) }}
                        </dd>
                    </dl>
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="4.3 Location and Access"
                :visible="true"
            >
                <template #sectionContent>
                    <dl v-if="locationAndAccess.length">
                        <template
                            v-for="(item, index) in locationAndAccess"
                            :key="index"
                        >
                            <dt>{{ item.visitName || `Visit ${index + 1}` }} - Location and Access</dt>
                            <dd>{{ getDisplayValue(item.location as AliasedNodeData) }}</dd>
                        </template>
                    </dl>
                    <div v-else>
                        <p>No location and access information available.</p>
                    </div>
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="4.4 Address and Legal Description"
                :visible="true"
            >
                <template #sectionContent>
                    <DetailsSection
                        section-title="BC Property Address"
                        :visible="true"
                    >
                        <template #sectionContent>
                            <dl v-if="props.data?.bc_property_address?.[0]?.aliased_data">
                                <dt v-if="!isEmpty(props.data.bc_property_address[0].aliased_data.street_number)">Street Number</dt>
                                <dd v-if="!isEmpty(props.data.bc_property_address[0].aliased_data.street_number)">
                                    {{ getDisplayValue(props.data.bc_property_address[0].aliased_data.street_number) }}
                                </dd>

                                <dt v-if="!isEmpty(props.data.bc_property_address[0].aliased_data.street_name)">Street Name</dt>
                                <dd v-if="!isEmpty(props.data.bc_property_address[0].aliased_data.street_name)">
                                    {{ getDisplayValue(props.data.bc_property_address[0].aliased_data.street_name) }}
                                </dd>

                                <dt v-if="!isEmpty(props.data.bc_property_address[0].aliased_data.city)">City</dt>
                                <dd v-if="!isEmpty(props.data.bc_property_address[0].aliased_data.city)">
                                    {{ getDisplayValue(props.data.bc_property_address[0].aliased_data.city) }}
                                </dd>

                                <dt v-if="!isEmpty(props.data.bc_property_address[0].aliased_data.postal_code)">Postal Code</dt>
                                <dd v-if="!isEmpty(props.data.bc_property_address[0].aliased_data.postal_code)">
                                    {{ getDisplayValue(props.data.bc_property_address[0].aliased_data.postal_code) }}
                                </dd>

                                <dt v-if="!isEmpty(props.data.bc_property_address[0].aliased_data.address_remarks)">Address Remarks</dt>
                                <dd v-if="!isEmpty(props.data.bc_property_address[0].aliased_data.address_remarks)">
                                    {{ getDisplayValue(props.data.bc_property_address[0].aliased_data.address_remarks) }}
                                </dd>
                            </dl>
                            <div v-else>
                                <p>No BC Property Address information available.</p>
                            </div>
                        </template>
                    </DetailsSection>

                    <DetailsSection
                        section-title="BC Property Legal Description"
                        :visible="true"
                    >
                        <template #sectionContent>
                            <dl v-if="props.data?.bc_property_address?.[0]?.aliased_data?.bc_property_legal_description?.[0]?.aliased_data">
                                <dt v-if="!isEmpty(props.data.bc_property_address[0].aliased_data.bc_property_legal_description[0].aliased_data.pid)">PID</dt>
                                <dd v-if="!isEmpty(props.data.bc_property_address[0].aliased_data.bc_property_legal_description[0].aliased_data.pid)">
                                    {{ getDisplayValue(props.data.bc_property_address[0].aliased_data.bc_property_legal_description[0].aliased_data.pid) }}
                                </dd>

                                <dt v-if="!isEmpty(props.data.bc_property_address[0].aliased_data.bc_property_legal_description[0].aliased_data.pin)">PIN</dt>
                                <dd v-if="!isEmpty(props.data.bc_property_address[0].aliased_data.bc_property_legal_description[0].aliased_data.pin)">
                                    {{ getDisplayValue(props.data.bc_property_address[0].aliased_data.bc_property_legal_description[0].aliased_data.pin) }}
                                </dd>

                                <dt v-if="!isEmpty(props.data.bc_property_address[0].aliased_data.bc_property_legal_description[0].aliased_data.legal_description)">Legal Description</dt>
                                <dd v-if="!isEmpty(props.data.bc_property_address[0].aliased_data.bc_property_legal_description[0].aliased_data.legal_description)">
                                    {{ getDisplayValue(props.data.bc_property_address[0].aliased_data.bc_property_legal_description[0].aliased_data.legal_description) }}
                                </dd>

                                <dt v-if="!isEmpty(props.data.bc_property_address[0].aliased_data.bc_property_legal_description[0].aliased_data.legal_address_remarks)">Legal Address Remarks</dt>
                                <dd v-if="!isEmpty(props.data.bc_property_address[0].aliased_data.bc_property_legal_description[0].aliased_data.legal_address_remarks)">
                                    {{ getDisplayValue(props.data.bc_property_address[0].aliased_data.bc_property_legal_description[0].aliased_data.legal_address_remarks) }}
                                </dd>
                            </dl>
                            <div v-else>
                                <p>No BC Property Legal Description information available.</p>
                            </div>
                        </template>
                    </DetailsSection>

                    <dl v-if="props.data?.address_remarks?.aliased_data">
                        <dt v-if="!isEmpty(props.data.address_remarks.aliased_data.address_and_legal_description_remarks)">Address and Legal Description Remarks</dt>
                        <dd v-if="!isEmpty(props.data.address_remarks.aliased_data.address_and_legal_description_remarks)">
                            {{ getDisplayValue(props.data.address_remarks.aliased_data.address_and_legal_description_remarks) }}
                        </dd>

                        <dt v-if="!isEmpty(props.data.address_remarks.aliased_data.entered_on)">Entered On</dt>
                        <dd v-if="!isEmpty(props.data.address_remarks.aliased_data.entered_on)">
                            {{ getDisplayValue(props.data.address_remarks.aliased_data.entered_on) }}
                        </dd>

                        <dt v-if="!isEmpty(props.data.address_remarks.aliased_data.entered_by)">Entered By</dt>
                        <dd v-if="!isEmpty(props.data.address_remarks.aliased_data.entered_by)">
                            {{ getDisplayValue(props.data.address_remarks.aliased_data.entered_by) }}
                        </dd>
                    </dl>
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="4.5 Elevation"
                :visible="true"
            >
                <template #sectionContent>
                    <DetailsSection
                        section-title="GIS Elevation"
                        :visible="true"
                    >
                        <template #sectionContent>
                            <dl v-if="props.data?.elevation?.aliased_data">
                                <dt v-if="!isEmpty(props.data.elevation.aliased_data.gis_lower_elevation)">GIS Lower Elevation (m asl)</dt>
                                <dd v-if="!isEmpty(props.data.elevation.aliased_data.gis_lower_elevation)">
                                    {{ getDisplayValue(props.data.elevation.aliased_data.gis_lower_elevation) }}
                                </dd>

                                <dt v-if="!isEmpty(props.data.elevation.aliased_data.gis_upper_elevation)">GIS Upper Elevation (m asl)</dt>
                                <dd v-if="!isEmpty(props.data.elevation.aliased_data.gis_upper_elevation)">
                                    {{ getDisplayValue(props.data.elevation.aliased_data.gis_upper_elevation) }}
                                </dd>
                            </dl>
                            <div v-else>
                                <p>No GIS elevation information available.</p>
                            </div>
                        </template>
                    </DetailsSection>

                    <DetailsSection
                        section-title="Elevation Comments"
                        :visible="true"
                    >
                        <template #sectionContent>
                            <dl v-if="props.data?.elevation?.aliased_data?.elevation_comments?.length">
                                <template
                                    v-for="(comment, index) in props.data.elevation.aliased_data.elevation_comments"
                                    :key="index"
                                >
                                    <dt>Elevation Comments {{ index + 1 }}</dt>
                                    <dd v-html="getDisplayValue(comment.aliased_data?.elevation_comments)"></dd>
                                </template>
                            </dl>
                            <div v-else>
                                <p>No elevation comments available.</p>
                            </div>
                        </template>
                    </DetailsSection>
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="4.6 Biogeography"
                :visible="true"
            >
                <template #sectionContent>
                    <StandardDataTable
                        :table-data="props.data?.biogeography ?? []"
                        :column-definitions="biogeographyColumns"
                        title="Biogeography"
                        :initial-sort-field-index="0"
                    />
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>
