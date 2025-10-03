<script setup lang="ts">
import { ref, computed, type Ref } from 'vue';
import type { DetailsData } from '@/bcap/types.ts';
import { formatDateTime } from '@/bcap/util.ts';
import type { EditLogData } from '@/bcgov_arches_common/types.ts';
import EditLog from '@/bcgov_arches_common/components/EditLog/EditLog.vue';
import ArchaeologicalSite from '@/bcap/components/pages/details/ArchaeologicalSite/ArchaeologicalSiteDetails.vue';
import SiteVisit from '@/bcap/components/pages/details/SiteVisit/SiteVisitDetails.vue';
import HcaPermit from '@/bcap/components/pages/details/HcaPermit/HcaPermitDetails.vue';
import Contributor from '@/bcap/components/pages/details/Contributor/ContributorDetails.vue';
import Government from '@/bcap/components/pages/details/Government/GovernmentDetails.vue';
import HriaDiscontinuedData from '@/bcap/components/pages/details/HriaDiscontinuedData/HriaDiscontinuedDataDetails.vue';
import LegislativeAct from '@/bcap/components/pages/details/LegislativeAct/LegislativeActDetails.vue';
import Repository from '@/bcap/components/pages/details/Repository/RepositoryDetails.vue';
import SectionControls from '@/bcap/components/SectionControls.vue';
import { collectTileIds } from '@/bcgov_arches_common/composables/useTileEditLog.ts';
import {
    useResourceData,
    useRelatedResourceData,
} from '@/bcap/composables/useResourceData.ts';
import type { ArchaeologySiteSchema } from '@/bcap/schema/ArchaeologySiteSchema.ts';
import type { SiteVisitSchema } from '@/bcap/schema/SiteVisitSchema.ts';
import type { AliasedTileData } from '@/arches_component_lab/types.ts';

const props = withDefaults(
    defineProps<{
        data: DetailsData;
        languageCode?: string;
    }>(),
    {
        languageCode: 'en',
    },
);

const hideEmptySections = ref(false);
const forceCollapsed = ref<boolean | undefined>(undefined);
const editLogData = ref<EditLogData>({});

const resourceId = computed(() => props.data?.resourceinstance_id);

const { data: resourceData } = useResourceData<
    ArchaeologySiteSchema | SiteVisitSchema
>(props.data.graph_slug, resourceId);

const siteVisitResourceIdComputed: Ref<string | undefined> = computed(() => {
    return props.data.graph_slug === 'archaeological_site'
        ? resourceId.value
        : undefined;
});

const { data: relatedSiteVisits } = useRelatedResourceData<SiteVisitSchema>(
    'site_visit',
    siteVisitResourceIdComputed,
);

const archSiteTileIds = computed(() => {
    const tileIds: string[] = [];
    if (!resourceData.value || props.data.graph_slug !== 'archaeological_site')
        return tileIds;

    const data = resourceData.value as ArchaeologySiteSchema;
    const editLogTiles = [
        [
            'aliased_data',
            'identification_and_registration',
            'aliased_data',
            'authority',
        ],
        [
            'aliased_data',
            'identification_and_registration',
            'aliased_data',
            'site_names',
        ],
        [
            'aliased_data',
            'identification_and_registration',
            'aliased_data',
            'site_decision',
        ],
        ['aliased_data', 'heritage_site_location', '0', 'tenure_remarks'],
        ['aliased_data', 'heritage_site_location', '0', 'address_remarks'],
        [
            'aliased_data',
            'archaeological_data',
            'aliased_data',
            'site_typology_remarks',
        ],
        [
            'aliased_data',
            'ancestral_remains',
            'aliased_data',
            'restricted_ancestral_remains_remark',
        ],
        [
            'aliased_data',
            'remarks_and_restricted_information',
            'aliased_data',
            'general_remark_information',
        ],
        [
            'aliased_data',
            'remarks_and_restricted_information',
            'aliased_data',
            'hca_contravention',
        ],
        [
            'aliased_data',
            'remarks_and_restricted_information',
            'aliased_data',
            'conviction',
        ],
    ];
    return collectTileIds(data, editLogTiles);
});

const siteVisitTileMap = computed(() => {
    const tileMap = new Map<string, string[]>();
    if (props.data.graph_slug !== 'archaeological_site') return tileMap;

    const siteVisits = (relatedSiteVisits.value || []) as SiteVisitSchema[];
    siteVisits.forEach((visit) => {
        const visitTileIds: string[] = [];

        const siteVisitDetailsTile = visit.aliased_data?.site_visit_details;
        if (siteVisitDetailsTile?.tileid) {
            visitTileIds.push(siteVisitDetailsTile.tileid);
        }

        const remarksRecs =
            visit.aliased_data?.remarks_and_recommendations?.aliased_data;
        if (remarksRecs) {
            if (remarksRecs.recommendation) {
                remarksRecs.recommendation.forEach((rec: AliasedTileData) => {
                    if (rec.tileid) visitTileIds.push(rec.tileid);
                });
            }
            if (remarksRecs.general_remark) {
                remarksRecs.general_remark.forEach(
                    (remark: AliasedTileData) => {
                        if (remark.tileid) visitTileIds.push(remark.tileid);
                    },
                );
            }
        }

        const identification = visit.aliased_data?.identification?.aliased_data;
        if (identification) {
            if (identification.temporary_number?.tileid) {
                visitTileIds.push(identification.temporary_number.tileid);
            }
            if (identification.new_site_names) {
                identification.new_site_names.forEach(
                    (name: AliasedTileData) => {
                        if (name.tileid) visitTileIds.push(name.tileid);
                    },
                );
            }
        }

        const teamTile =
            visit.aliased_data?.site_visit_details?.aliased_data
                ?.site_visit_team_n1;
        if (teamTile?.aliased_data?.team_member) {
            teamTile.aliased_data.team_member.forEach(
                (member: AliasedTileData) => {
                    if (member.tileid) visitTileIds.push(member.tileid);
                },
            );
        }

        if (visitTileIds.length > 0) {
            tileMap.set(visit.resourceinstanceid, visitTileIds);
        }
    });

    return tileMap;
});

const fetchSiteVisitEditLogs = async () => {
    if (
        props.data.graph_slug !== 'archaeological_site' ||
        siteVisitTileMap.value.size === 0
    )
        return;

    const promises = Array.from(siteVisitTileMap.value.entries()).map(
        async ([visitResourceId, tileIds]) => {
            const results: EditLogData = {};

            const fetchPromises = tileIds.map(async (tileId) => {
                try {
                    const response = await fetch(
                        `/bcap/api/resources/site_visit/${visitResourceId}/edit-log/?tile_id=${tileId}`,
                    );
                    if (!response.ok) return null;

                    const data = await response.json();
                    return {
                        tileId,
                        editLog: {
                            entered_on:
                                formatDateTime(data.modified_on) || null,
                            entered_by: data.modified_by || null,
                        },
                    };
                } catch (error) {
                    console.error(
                        `Error fetching edit log for tile ${tileId}:`,
                        error,
                    );
                    return null;
                }
            });

            const tileResults = await Promise.all(fetchPromises);
            tileResults.forEach((result) => {
                if (result) {
                    results[`tile_${result.tileId}`] = result.editLog;
                }
            });

            return results;
        },
    );

    const allResults = await Promise.all(promises);
    allResults.forEach((result) => {
        Object.assign(editLogData.value, result);
    });
};

const allTileIds = computed(() => {
    const tileIds: string[] = [];

    if (!resourceData.value) return tileIds;

    if (props.data.graph_slug === 'archaeological_site') {
        return archSiteTileIds.value;
    } else if (props.data.graph_slug === 'site_visit') {
        const data = resourceData.value as SiteVisitSchema;

        const siteVisitDetailsTile = data.aliased_data?.site_visit_details;
        if (siteVisitDetailsTile?.tileid) {
            tileIds.push(siteVisitDetailsTile.tileid);
        }

        const remarksRecs =
            data.aliased_data?.remarks_and_recommendations?.aliased_data;
        if (remarksRecs) {
            if (remarksRecs.recommendation) {
                remarksRecs.recommendation.forEach((rec: AliasedTileData) => {
                    if (rec.tileid) tileIds.push(rec.tileid);
                });
            }
            if (remarksRecs.general_remark) {
                remarksRecs.general_remark.forEach(
                    (remark: AliasedTileData) => {
                        if (remark.tileid) tileIds.push(remark.tileid);
                    },
                );
            }
        }

        const identification = data.aliased_data?.identification?.aliased_data;
        if (identification) {
            if (identification.temporary_number?.tileid) {
                tileIds.push(identification.temporary_number.tileid);
            }
            if (identification.new_site_names) {
                identification.new_site_names.forEach(
                    (name: AliasedTileData) => {
                        if (name.tileid) tileIds.push(name.tileid);
                    },
                );
            }
        }

        const teamTile =
            data.aliased_data?.site_visit_details?.aliased_data
                ?.site_visit_team_n1;
        if (teamTile?.aliased_data?.team_member) {
            teamTile.aliased_data.team_member.forEach(
                (member: AliasedTileData) => {
                    if (member.tileid) tileIds.push(member.tileid);
                },
            );
        }
    }

    return tileIds;
});

const handleVisibilityChange = (hideEmpty: boolean) => {
    hideEmptySections.value = hideEmpty;
};

const handleCollapseAll = () => {
    forceCollapsed.value = true;
    setTimeout(() => {
        forceCollapsed.value = undefined;
    }, 100);
};

const handleExpandAll = () => {
    forceCollapsed.value = false;
    setTimeout(() => {
        forceCollapsed.value = undefined;
    }, 100);
};

const handlePopulateAllFields = async (results: EditLogData) => {
    Object.assign(editLogData.value, results);

    if (props.data.graph_slug === 'archaeological_site') {
        await fetchSiteVisitEditLogs();
    }
};
</script>

<template>
    <div
        class="details-page-container"
        :class="{ 'hide-empty': hideEmptySections }"
    >
        <div class="container">
            <SectionControls
                @visibility-changed="handleVisibilityChange"
                @collapse-all="handleCollapseAll"
                @expand-all="handleExpandAll"
            >
                <EditLog
                    v-if="
                        resourceId &&
                        allTileIds.length > 0 &&
                        ['archaeological_site', 'site_visit'].includes(
                            props.data.graph_slug,
                        )
                    "
                    :resource-id="resourceId"
                    :graph="props.data.graph_slug"
                    :tile-ids="allTileIds"
                    @populate-all-fields="handlePopulateAllFields"
                />
            </SectionControls>
        </div>

        <ArchaeologicalSite
            v-if="props.data.graph_slug === 'archaeological_site'"
            :data="props.data"
            :language-code="props.languageCode"
            :force-collapsed="forceCollapsed"
            :edit-log-data="editLogData"
        />
        <SiteVisit
            v-else-if="props.data.graph_slug === 'site_visit'"
            :data="props.data"
            :language-code="languageCode"
            :force-collapsed="forceCollapsed"
            :edit-log-data="editLogData"
        />
        <HcaPermit
            v-else-if="props.data.graph_slug === 'hca_permit'"
            :data="props.data"
            :language-code="languageCode"
            :force-collapsed="forceCollapsed"
        />
        <Contributor
            v-else-if="props.data.graph_slug === 'contributor'"
            :data="props.data"
            :language-code="languageCode"
            :force-collapsed="forceCollapsed"
        />
        <Government
            v-else-if="props.data.graph_slug === 'local_government'"
            :data="props.data"
            :language-code="languageCode"
            :force-collapsed="forceCollapsed"
        />
        <HriaDiscontinuedData
            v-else-if="props.data.graph_slug === 'hria_discontinued_data'"
            :data="props.data"
            :language-code="languageCode"
            :force-collapsed="forceCollapsed"
        />
        <LegislativeAct
            v-else-if="props.data.graph_slug === 'legislative_act'"
            :data="props.data"
            :language-code="languageCode"
            :force-collapsed="forceCollapsed"
        />
        <Repository
            v-else-if="props.data.graph_slug === 'repository'"
            :data="props.data"
            :language-code="languageCode"
            :force-collapsed="forceCollapsed"
        />
        <div v-else>
            Details page for {{ props.data.graph_slug }} not implemented yet.
        </div>
    </div>
</template>

<style>
.details-page-container {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.details-page-container.hide-empty .empty-section {
    display: none !important;
}

.container {
    gap: 0.5rem;
}
</style>
