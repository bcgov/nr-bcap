<script setup lang="ts">
import type { DetailsData } from '@/bcap/types.ts';
import ArchaeologicalSite from '@/bcap/components/pages/details/ArchaeologicalSite/ArchaeologicalSite.vue';
import SiteVisit from '@/bcap/components/pages/details/SiteVisit/SiteVisit.vue';

const props = withDefaults(
    defineProps<{
        data: DetailsData;
        languageCode?: string;
    }>(),
    {
        languageCode: 'en',
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
        v-else-if="props.data.graph_slug == 'site_visit'"
        :data="props.data"
        :language-code="languageCode"
    ></SiteVisit>
    <div v-else>
        Details page for {{ props.data.graph_slug }} not implemented yet.
    </div>
</template>

<style>
.container {
    gap: 0.5rem;
}
</style>
