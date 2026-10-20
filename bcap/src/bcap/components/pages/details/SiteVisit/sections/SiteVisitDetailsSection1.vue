<script setup lang="ts">
import { computed } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import EmptyState from '@/bcap/components/EmptyState.vue';
import StandardDataTable from '@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue';
import type { SiteVisit } from '@/bcap/client/types.gen.ts';
import type { AliasedTileDataWithAudit } from '@/bcgov_arches_common/types.ts';

const props = withDefaults(
    defineProps<{
        data: SiteVisit | undefined;
        loading?: boolean;
    }>(),
    { loading: false },
);

const current = computed(() => props.data);

const hasLocationData = computed(() => {
    return !!current.value?.aliased_data?.site_visit_location;
});

const hasLocationAndAccess = computed(() => {
    return current.value?.aliased_data?.site_visit_location?.aliased_data
        ?.location_and_access?.aliased_data?.location_and_access?.node_value;
});

const hasGeoJsonData = computed(() => {
    return current.value?.aliased_data?.site_visit_location?.aliased_data
        ?.spatial_location?.[0]?.aliased_data?.spatial_location?.node_value;
});

const hasBiogeography = computed(() => {
    let biogeographyData =
        current.value?.aliased_data?.site_visit_location?.aliased_data
            ?.biogeography;
    return biogeographyData && biogeographyData.length > 0;
});

const biogeographyRows = computed(
    () =>
        (current.value?.aliased_data?.site_visit_location?.aliased_data
            ?.biogeography || []) as unknown as AliasedTileDataWithAudit[],
);

const biogeographyColumns = [
    { field: 'biogeography_type', label: 'Type' },
    { field: 'biogeography_name', label: 'Name' },
    { field: 'biogeography_description', label: 'Description', isHtml: true },
];
</script>

<template>
    <DetailsSection
        section-title="1. Site Visit Location"
        :loading="props.loading"
        :visible="true"
    >
        <template #sectionContent>
            <DetailsSection
                section-title="Location and Access"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasLocationAndAccess }"
            >
                <template #sectionContent>
                    <div v-if="hasLocationData">
                        <dl>
                            <dt>Boundary Type</dt>
                            <dd
                                v-text="
                                    current?.aliased_data?.site_visit_location
                                        ?.aliased_data?.spatial_location?.[0]
                                        ?.aliased_data?.boundary_type
                                        ?.display_value
                                "
                            />
                            <dt>Boundary Description</dt>
                            <dd
                                v-html="
                                    current?.aliased_data?.site_visit_location
                                        ?.aliased_data?.spatial_location?.[0]
                                        ?.aliased_data?.boundary_description
                                        ?.display_value
                                "
                            />
                            <dt>Location and Access</dt>
                            <dd
                                v-html="
                                    current?.aliased_data?.site_visit_location
                                        ?.aliased_data?.location_and_access
                                        ?.aliased_data?.location_and_access
                                        ?.display_value
                                "
                            />
                        </dl>
                    </div>
                    <EmptyState v-else />
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
                        :table-data="biogeographyRows"
                        :column-definitions="biogeographyColumns"
                        :initial-sort-field-index="0"
                    />
                    <EmptyState
                        v-else
                        message="No biogeography information available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Site Visit Location (GeoJSON)"
                variant="subsection"
                :visible="false"
                :class="{ 'empty-section': !hasGeoJsonData }"
            >
                <template #sectionContent>
                    <div v-if="hasGeoJsonData">
                        <pre
                            style="
                                white-space: pre-wrap;
                                word-break: break-word;
                            "
                            >{{
                                JSON.stringify(
                                    current?.aliased_data?.site_visit_location
                                        ?.aliased_data?.spatial_location?.[0]
                                        ?.aliased_data?.spatial_location
                                        ?.node_value,
                                    null,
                                    2,
                                )
                            }}</pre>
                    </div>
                    <EmptyState
                        v-else
                        message="No site visit location data available."
                    />
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>
