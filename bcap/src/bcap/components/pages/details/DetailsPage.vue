<script setup lang="ts">
import type { DetailsData } from "@/bcap/types.ts";
import ArchaeologicalSite from "@/bcap/components/pages/details/ArchaeologicalSite/ArchaeologicalSite.vue";
import SiteVisit from "@/bcap/components/pages/details/SiteVisit/SiteVisit.vue";
import HcaPermit from "@/bcap/components/pages/details/HcaPermit/HcaPermit.vue";
import Contributor from "@/bcap/components/pages/details/Contributor/Contributor.vue";
import Government from "@/bcap/components/pages/details/Government/Government.vue";
import HriaDiscontinuedData from "@/bcap/components/pages/details/HriaDiscontinuedData/HriaDiscontinuedData.vue";
import LegislativeAct from "@/bcap/components/pages/details/LegislativeAct/LegislativeAct.vue";
import Repository from "@/bcap/components/pages/details/Repository/Repository.vue";

const props = withDefaults(
    defineProps<{
        data: DetailsData;
        languageCode?: string;
    }>(),
    {
        languageCode: "en",
    },
);
</script>
<template>
    <ArchaeologicalSite
        v-if="props.data.graph_slug === 'archaeological_site'"
        :data="props.data"
        :language-code="props.languageCode"
    ></ArchaeologicalSite>
    <SiteVisit
        v-else-if="props.data.graph_slug === 'site_visit'"
        :data="props.data"
        :language-code="languageCode"
    ></SiteVisit>
    <HcaPermit
        v-else-if="props.data.graph_slug === 'hca_permit'"
        :data="props.data"
        :language-code="languageCode"
    ></HcaPermit>
    <Contributor
        v-else-if="props.data.graph_slug === 'contributor'"
        :data="props.data"
        :language-code="languageCode"
    ></Contributor>
    <Government
        v-else-if="props.data.graph_slug === 'local_government'"
        :data="props.data"
        :language-code="languageCode"
    ></Government>
    <HriaDiscontinuedData
        v-else-if="props.data.graph_slug === 'hria_discontinued_data'"
        :data="props.data"
        :language-code="languageCode"
    ></HriaDiscontinuedData>
    <LegislativeAct
        v-else-if="props.data.graph_slug === 'legislative_act'"
        :data="props.data"
        :language-code="languageCode"
    ></LegislativeAct>
    <Repository
        v-else-if="props.data.graph_slug === 'repository'"
        :data="props.data"
        :language-code="languageCode"
    ></Repository>
    <div v-else>
        Details page for {{ props.data.graph_slug }} not implemented yet.
    </div>
</template>

<style>
.container {
    gap: 0.5rem;
}
</style>
