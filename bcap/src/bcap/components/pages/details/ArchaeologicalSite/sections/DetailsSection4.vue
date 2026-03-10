<script setup lang="ts">
import { computed, toRef } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import EmptyState from '@/bcap/components/EmptyState.vue';
import { getDisplayValue, isEmpty } from '@/bcap/util.ts';
import {
    useTileEditLog,
    useSingleTileEditLog,
} from '@/bcgov_arches_common/composables/useTileEditLog.ts';
import type { EditLogData } from '@/bcgov_arches_common/types.ts';
import { EDIT_LOG_FIELDS } from '@/bcgov_arches_common/constants.ts';
import StandardDataTable from '@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue';
import 'primeicons/primeicons.css';
import type {
    AliasedNodeData,
    AliasedTileData,
} from '@/arches_component_lab/types.ts';
import type { AliasedTileDataWithAudit } from '@/bcgov_arches_common/types.ts';
import type { SiteLocationTile } from '@/bcap/schema/ArchaeologySiteSchema.ts';
import type { SiteVisitSchema } from '@/bcap/schema/SiteVisitSchema.ts';
import type { HriaDiscontinuedDataSchema } from '@/bcap/schema/HriaDiscontinuedDataSchema.ts';

const props = withDefaults(
    defineProps<{
        data: SiteLocationTile | undefined;
        siteVisitData: SiteVisitSchema[];
        hriaData: HriaDiscontinuedDataSchema | undefined;
        loading?: boolean;
        languageCode?: string;
        forceCollapsed?: boolean;
        editLogData?: EditLogData;
        showAuditFields?: boolean;
    }>(),
    {
        languageCode: 'en',
        loading: false,
        forceCollapsed: undefined,
        editLogData: () => ({}),
        showAuditFields: false,
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

const elevationCommentsColumns = computed(() => [
    { field: 'elevation_comments', label: 'Elevation Remarks', isHtml: true },
    {
        field: EDIT_LOG_FIELDS.ENTERED_ON,
        label: 'Entered On',
        visible: props.showAuditFields,
    },
    {
        field: EDIT_LOG_FIELDS.ENTERED_BY,
        label: 'Entered By',
        visible: props.showAuditFields,
    },
]);

const discontinuedTenureColumns = [
    { field: 'site_jurisdiction', label: 'Jurisdiction' },
    { field: 'tenure_type', label: 'Tenure/Reserves Type' },
    { field: 'tenure_identifier', label: 'Description' },
    { field: 'tenure_remarks', label: 'Tenure Remarks' },
    { field: 'jurisdiction_entered_date', label: 'Modified On' },
    { field: 'jurisdiction_entered_by', label: 'Modified By' },
];

const tenureRemarksColumns = computed(() => [
    { field: 'tenure_remarks', label: 'Tenure Remarks' },
    {
        field: EDIT_LOG_FIELDS.ENTERED_ON,
        label: 'Entered On',
        visible: props.showAuditFields,
    },
    {
        field: EDIT_LOG_FIELDS.ENTERED_BY,
        label: 'Entered By',
        visible: props.showAuditFields,
    },
]);

const addressRemarksColumns = computed(() => [
    {
        field: 'address_and_legal_description_remarks',
        label: 'Address and Legal Description Remarks',
        isHtml: true,
    },
    {
        field: EDIT_LOG_FIELDS.ENTERED_ON,
        label: 'Entered On',
        visible: props.showAuditFields,
    },
    {
        field: EDIT_LOG_FIELDS.ENTERED_BY,
        label: 'Entered By',
        visible: props.showAuditFields,
    },
]);

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

const legalDescriptionColumns = [
    { field: 'pid', label: 'PID' },
    { field: 'pin', label: 'PIN' },
    { field: 'legal_description', label: 'Legal Description' },
];

const streetAddressColumns = [
    { field: 'street_number', label: 'Street Number' },
    { field: 'street_name', label: 'Street Name' },
    { field: 'city', label: 'City' },
    { field: 'postal_code', label: 'Postal Code' },
    { field: 'address_remarks', label: 'Address Remarks' },
];

const hasCoordinates = computed(() => {
    const data = props.data as Record<string, unknown> | undefined;
    return (
        data?.coordinates &&
        (data.coordinates as Record<string, unknown>)?.aliased_data
    );
});

const hasTenureAndReserves = computed(() => {
    const data = props.data as Record<string, unknown> | undefined;
    const tenure = data?.tenure_and_reserves || data?.site_tenure;
    if (!tenure) return false;
    if (Array.isArray(tenure)) return tenure.length > 0;
    return !!tenure;
});

const hasTenureRemarks = computed(() => {
    const data = props.data as Record<string, unknown> | undefined;
    const remarks = data?.tenure_remarks;
    return remarks && Array.isArray(remarks) && remarks.length > 0;
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

const allBcPropertyAddresses = computed(() => {
    const data = props.data as Record<string, unknown> | undefined;
    const addresses = data?.bc_property_address;
    if (!addresses || !Array.isArray(addresses)) return [];
    return addresses;
});

function hasDisplayValue(node: unknown): boolean {
    if (!node || typeof node !== 'object') return false;
    const n = node as { display_value?: string };
    return !!n.display_value && n.display_value.trim() !== '';
}

const streetAddressTableData = computed(() => {
    return allBcPropertyAddresses.value.filter((addr) => {
        const ad = addr.aliased_data;
        if (!ad) return false;
        return (
            hasDisplayValue(ad.street_number) ||
            hasDisplayValue(ad.street_name) ||
            hasDisplayValue(ad.city) ||
            hasDisplayValue(ad.postal_code) ||
            hasDisplayValue(ad.address_remarks)
        );
    });
});

const hasBcPropertyAddress = computed(() => {
    return streetAddressTableData.value.length > 0;
});

const allLegalDescriptions = computed((): AliasedTileDataWithAudit[] => {
    const results: AliasedTileDataWithAudit[] = [];
    allBcPropertyAddresses.value.forEach((addr) => {
        const legalDescs = addr.aliased_data?.bc_property_legal_description;
        if (legalDescs && Array.isArray(legalDescs)) {
            legalDescs.forEach((ld: unknown) => {
                const tile = ld as { aliased_data?: Record<string, unknown> };
                if (tile.aliased_data) {
                    const ad = tile.aliased_data;
                    if (
                        hasDisplayValue(ad.legal_description) ||
                        hasDisplayValue(ad.pid) ||
                        hasDisplayValue(ad.pin)
                    ) {
                        results.push(tile as AliasedTileDataWithAudit);
                    }
                }
            });
        }
    });
    return results;
});

const allLegalAddressRemarks = computed(() => {
    const results: unknown[] = [];
    allBcPropertyAddresses.value.forEach((addr) => {
        const legalDescs = addr.aliased_data?.bc_property_legal_description;
        if (legalDescs && Array.isArray(legalDescs)) {
            legalDescs.forEach((ld: unknown) => {
                const tile = ld as { aliased_data?: Record<string, unknown> };
                if (tile.aliased_data) {
                    if (
                        hasDisplayValue(tile.aliased_data.legal_address_remarks)
                    ) {
                        results.push(tile);
                    }
                }
            });
        }
    });
    return results;
});

const addressRemarksTableData = computed((): AliasedTileDataWithAudit[] => {
    const remarks: AliasedTileDataWithAudit[] = [];

    allLegalAddressRemarks.value.forEach((tile) => {
        const t = tile as { aliased_data?: Record<string, unknown> };
        if (t.aliased_data?.legal_address_remarks) {
            remarks.push({
                ...t,
                aliased_data: {
                    address_and_legal_description_remarks:
                        t.aliased_data.legal_address_remarks,
                },
            } as unknown as AliasedTileDataWithAudit);
        }
    });

    if (
        addressRemarksData.value?.aliased_data
            ?.address_and_legal_description_remarks
    ) {
        const node = addressRemarksData.value.aliased_data
            .address_and_legal_description_remarks as AliasedNodeData;
        if (hasDisplayValue(node)) {
            remarks.push({
                ...addressRemarksData.value,
                aliased_data: {
                    address_and_legal_description_remarks: node,
                },
            } as AliasedTileDataWithAudit);
        }
    }

    return remarks;
});

const hasAddressRemarks = computed(() => {
    return addressRemarksTableData.value.length > 0;
});

const hasBcPropertyLegalDescription = computed(() => {
    return allLegalDescriptions.value.length > 0;
});

const hasDiscontinuedAddress = computed(() => {
    const disc = (
        props.hriaData?.aliased_data as unknown as {
            discontinued_address_attributes?: unknown[];
        }
    )?.discontinued_address_attributes;
    return disc && Array.isArray(disc) && disc.length > 0;
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
    const elev = props.data?.elevation?.aliased_data;
    return (
        elev &&
        (!isEmpty(elev.gis_lower_elevation) ||
            !isEmpty(elev.gis_upper_elevation))
    );
});

const hasElevationComments = computed(() => {
    return (
        props.data?.elevation?.aliased_data?.elevation_comments &&
        props.data.elevation.aliased_data.elevation_comments.length > 0
    );
});

const hasElevation = computed(() => {
    return hasGisElevation.value || hasElevationComments.value;
});

const hasBiogeography = computed(() => {
    const data = props.data as Record<string, unknown> | undefined;
    const bio = data?.biogeography;
    return bio && Array.isArray(bio) && bio.length > 0;
});

const tenureRemarksData = computed((): AliasedTileData[] => {
    const data = props.data as Record<string, unknown> | undefined;
    const remarks = data?.tenure_remarks;
    return (
        remarks && Array.isArray(remarks) ? remarks : []
    ) as AliasedTileData[];
});

const addressRemarksSource = computed((): AliasedTileData | undefined => {
    const data = props.data as Record<string, unknown> | undefined;
    return data?.address_remarks as AliasedTileData | undefined;
});

const elevationCommentsData = computed(
    () => props.data?.elevation?.aliased_data?.elevation_comments || [],
);

const { processedData: tenureRemarksTableData } = useTileEditLog(
    tenureRemarksData,
    toRef(props, 'editLogData'),
);

const { processedData: addressRemarksData } = useSingleTileEditLog(
    addressRemarksSource,
    toRef(props, 'editLogData'),
);

const { processedData: elevationCommentsTableData } = useTileEditLog(
    elevationCommentsData,
    toRef(props, 'editLogData'),
);
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
                                    (props.data as any)?.coordinates
                                        ?.aliased_data?.utm_zone,
                                )
                            "
                        >
                            UTM Zone
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    (props.data as any)?.coordinates
                                        ?.aliased_data?.utm_zone,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    (props.data as any)?.coordinates
                                        ?.aliased_data?.utm_zone,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    (props.data as any)?.coordinates
                                        ?.aliased_data?.utm_easting,
                                )
                            "
                        >
                            UTM Easting
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    (props.data as any)?.coordinates
                                        ?.aliased_data?.utm_easting,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    (props.data as any)?.coordinates
                                        ?.aliased_data?.utm_easting,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    (props.data as any)?.coordinates
                                        ?.aliased_data?.utm_northing,
                                )
                            "
                        >
                            UTM Northing
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    (props.data as any)?.coordinates
                                        ?.aliased_data?.utm_northing,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    (props.data as any)?.coordinates
                                        ?.aliased_data?.utm_northing,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    (props.data as any)?.coordinates
                                        ?.aliased_data?.latitude,
                                )
                            "
                        >
                            Latitude
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    (props.data as any)?.coordinates
                                        ?.aliased_data?.latitude,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    (props.data as any)?.coordinates
                                        ?.aliased_data?.latitude,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    (props.data as any)?.coordinates
                                        ?.aliased_data?.longitude,
                                )
                            "
                        >
                            Longitude
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    (props.data as any)?.coordinates
                                        ?.aliased_data?.longitude,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    (props.data as any)?.coordinates
                                        ?.aliased_data?.longitude,
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
                        section-title="Tenure and Reserves"
                        variant="subsection"
                        :visible="true"
                        :class="{ 'empty-section': !hasTenureAndReserves }"
                    >
                        <template #sectionContent>
                            <StandardDataTable
                                v-if="hasTenureAndReserves"
                                :table-data="
                                    (props.data as any)?.tenure_and_reserves ??
                                    (props.data as any)?.site_tenure ??
                                    []
                                "
                                :column-definitions="tenureColumns"
                                :initial-sort-field-index="0"
                            />
                            <EmptyState
                                v-else
                                message="No tenure and reserves information available."
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
                                :table-data="tenureRemarksTableData"
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
                                <StandardDataTable
                                    v-if="hasBcPropertyAddress"
                                    :table-data="streetAddressTableData"
                                    :column-definitions="streetAddressColumns"
                                />
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
                                <StandardDataTable
                                    v-if="hasBcPropertyLegalDescription"
                                    :table-data="allLegalDescriptions"
                                    :column-definitions="
                                        legalDescriptionColumns
                                    "
                                />
                                <EmptyState
                                    v-else
                                    message="No legal description information available."
                                />
                            </template>
                        </DetailsSection>

                        <DetailsSection
                            section-title="Address and Legal Description Remarks (Branch only)"
                            variant="subsection"
                            :visible="true"
                            :class="{
                                'empty-section': !hasAddressRemarks,
                            }"
                        >
                            <template #sectionContent>
                                <StandardDataTable
                                    v-if="hasAddressRemarks"
                                    :table-data="addressRemarksTableData"
                                    :column-definitions="addressRemarksColumns"
                                />
                                <EmptyState
                                    v-else
                                    message="No address remarks available."
                                />
                            </template>
                        </DetailsSection>

                        <DetailsSection
                            section-title="Discontinued Attributes"
                            variant="subsection"
                            :visible="true"
                            :class="{
                                'empty-section': !hasDiscontinuedAddress,
                            }"
                        >
                            <template #sectionContent>
                                <StandardDataTable
                                    v-if="
                                        hasDiscontinuedAddress &&
                                        (props.hriaData?.aliased_data as any)
                                            ?.discontinued_address_attributes
                                    "
                                    :table-data="
                                        (props.hriaData?.aliased_data as any)
                                            ?.discontinued_address_attributes
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
                                                props.data?.elevation
                                                    ?.aliased_data
                                                    ?.gis_lower_elevation,
                                            )
                                        "
                                    >
                                        Lower (m asl)
                                    </dt>
                                    <dd
                                        v-if="
                                            !isEmpty(
                                                props.data?.elevation
                                                    ?.aliased_data
                                                    ?.gis_lower_elevation,
                                            )
                                        "
                                    >
                                        {{
                                            getDisplayValue(
                                                props.data?.elevation
                                                    ?.aliased_data
                                                    ?.gis_lower_elevation,
                                            )
                                        }}
                                    </dd>

                                    <dt
                                        v-if="
                                            !isEmpty(
                                                props.data?.elevation
                                                    ?.aliased_data
                                                    ?.gis_upper_elevation,
                                            )
                                        "
                                    >
                                        Upper (m asl)
                                    </dt>
                                    <dd
                                        v-if="
                                            !isEmpty(
                                                props.data?.elevation
                                                    ?.aliased_data
                                                    ?.gis_upper_elevation,
                                            )
                                        "
                                    >
                                        {{
                                            getDisplayValue(
                                                props.data?.elevation
                                                    ?.aliased_data
                                                    ?.gis_upper_elevation,
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
                                <StandardDataTable
                                    v-if="hasElevationComments"
                                    :table-data="elevationCommentsTableData"
                                    :column-definitions="
                                        elevationCommentsColumns
                                    "
                                    :initial-sort-field-index="1"
                                />
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
                        :table-data="(props.data as any)?.biogeography ?? []"
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
