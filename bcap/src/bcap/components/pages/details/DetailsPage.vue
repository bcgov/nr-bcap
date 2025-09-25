<script setup lang="ts">
import { ref } from 'vue';
import type { DetailsData } from '@/bcap/types.ts';
import ArchaeologicalSite from '@/bcap/components/pages/details/ArchaeologicalSite/ArchaeologicalSiteDetails.vue';
import SiteVisit from '@/bcap/components/pages/details/SiteVisit/SiteVisitDetails.vue';
import HcaPermit from '@/bcap/components/pages/details/HcaPermit/HcaPermitDetails.vue';
import Contributor from '@/bcap/components/pages/details/Contributor/ContributorDetails.vue';
import Government from '@/bcap/components/pages/details/Government/GovernmentDetails.vue';
import HriaDiscontinuedData from '@/bcap/components/pages/details/HriaDiscontinuedData/HriaDiscontinuedDataDetails.vue';
import LegislativeAct from '@/bcap/components/pages/details/LegislativeAct/LegislativeActDetails.vue';
import Repository from '@/bcap/components/pages/details/Repository/RepositoryDetails.vue';
import SectionControls from '@/bcap/components/SectionControls.vue';

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
            />
        </div>

        <ArchaeologicalSite
            v-if="props.data.graph_slug === 'archaeological_site'"
            :data="props.data"
            :language-code="props.languageCode"
            :force-collapsed="forceCollapsed"
        />
        <SiteVisit
            v-else-if="props.data.graph_slug === 'site_visit'"
            :data="props.data"
            :language-code="languageCode"
            :force-collapsed="forceCollapsed"
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
