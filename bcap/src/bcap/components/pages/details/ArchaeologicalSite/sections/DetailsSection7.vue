<script setup lang="ts">
import { computed, toRef } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import EmptyState from '@/bcap/components/EmptyState.vue';
import StandardDataTable from '@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue';
import { useTileEditLog } from '@/bcgov_arches_common/composables/useTileEditLog.ts';
import type { EditLogData } from '@/bcgov_arches_common/types.ts';
import { EDIT_LOG_FIELDS } from '@/bcgov_arches_common/constants.ts';
import type { ColumnDefinition } from '@/bcgov_arches_common/components/StandardDataTable/types.ts';
import type { AliasedTileData } from '@/arches_vue_components/types.ts';
import 'primeicons/primeicons.css';
import type {
    ArchaeologicalSiteAncestralRemainsTile,
    ArchaeologicalSiteRestrictedAncestralRemainsRemarkTile,
    SiteVisit,
} from '@/bcap/client/types.gen.ts';

const props = withDefaults(
    defineProps<{
        data: ArchaeologicalSiteAncestralRemainsTile | undefined;
        siteVisitData?: SiteVisit[];
        loading?: boolean;
        languageCode?: string;
        forceCollapsed?: boolean;
        editLogData?: EditLogData;
        showAuditFields?: boolean;
    }>(),
    {
        siteVisitData: () => [],
        languageCode: 'en',
        loading: false,
        forceCollapsed: undefined,
        editLogData: () => ({}),
        showAuditFields: false,
    },
);

const siteVisitAncestralRemainsData = computed(() => {
    const remains: AliasedTileData[] = [];
    props.siteVisitData.forEach((sv) => {
        const remainsRows = sv.aliased_data?.ancestral_remains ?? [];
        remainsRows.forEach((tile) => {
            remains.push(tile as unknown as AliasedTileData);
        });
    });
    return remains;
});

const hasSiteVisitAncestralRemainsData = computed(
    () => siteVisitAncestralRemainsData.value.length > 0,
);

const siteVisitAncestralRemainsColumns = computed<ColumnDefinition[]>(() => [
    { field: 'ancestral_remains_type', label: 'Type' },
    { field: 'ancestral_remains_status', label: 'Status' },
    { field: 'ancestral_remains_remarks', label: 'Remarks', isHtml: true },
    { field: 'multiple_burials', label: 'Multiple Burials' },
    {
        field: 'minimum_number_of_individuals',
        label: 'Minimum # of Individuals',
    },
    { field: 'ancestral_remains_repository', label: 'Repository' },
]);

const restrictedRemainsDataRaw = computed(
    (): ArchaeologicalSiteRestrictedAncestralRemainsRemarkTile[] => {
        const remark =
            props.data?.aliased_data?.restricted_ancestral_remains_remark;
        if (!remark) return [];

        return Array.isArray(remark) ? remark : [remark];
    },
);

const { processedData: restrictedRemainsTableData } = useTileEditLog(
    restrictedRemainsDataRaw as unknown as ReturnType<
        typeof computed<AliasedTileData[]>
    >,
    toRef(props, 'editLogData'),
);

const hasRestrictedRemainsInfo = computed(() => {
    return (
        restrictedRemainsTableData.value &&
        restrictedRemainsTableData.value.length > 0
    );
});

const restrictedRemainsColumns = computed<ColumnDefinition[]>(() => {
    return [
        {
            field: 'restricted_ancestral_remains_remark',
            label: 'Restricted Ancestral Remains Remarks',
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
    ];
});
</script>

<template>
    <DetailsSection
        section-title="7. Ancestral Remains"
        :loading="props.loading"
        :visible="true"
        :force-collapsed="props.forceCollapsed"
    >
        <template #sectionContent>
            <StandardDataTable
                v-if="hasSiteVisitAncestralRemainsData"
                :table-data="siteVisitAncestralRemainsData"
                :column-definitions="siteVisitAncestralRemainsColumns"
            />
            <EmptyState
                v-else
                message="No ancestral remains data available."
            />

            <DetailsSection
                section-title="Restricted Ancestral Remains Information"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasRestrictedRemainsInfo }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasRestrictedRemainsInfo"
                        :table-data="restrictedRemainsTableData"
                        :column-definitions="restrictedRemainsColumns"
                    />
                    <EmptyState
                        v-else
                        message="No restricted ancestral remains information available."
                    />
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>
