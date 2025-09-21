<script setup lang="ts">
import { ref, watchEffect } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import { getResourceData } from '@/bcap/components/pages/api.ts';
import 'primeicons/primeicons.css';
import Section1 from '@/bcap/components/pages/details/SiteVisit/sections/SiteVisitDetailsSection1.vue';
import Section2 from '@/bcap/components/pages/details/SiteVisit/sections/SiteVisitDetailsSection2.vue';
import Section3 from '@/bcap/components/pages/details/SiteVisit/sections/SiteVisitDetailsSection3.vue';
import Section4 from '@/bcap/components/pages/details/SiteVisit/sections/SiteVisitDetailsSection4.vue';
import Section5 from '@/bcap/components/pages/details/SiteVisit/sections/SiteVisitDetailsSection5.vue';
import Section6 from '@/bcap/components/pages/details/SiteVisit/sections/SiteVisitDetailsSection6.vue';
import DataTable from 'primevue/datatable';
import type { DetailsData } from '@/bcap/types.ts';
import type { SiteVisitSchema } from '@/bcap/schema/SiteVisitSchema.ts';

const props = withDefaults(
    defineProps<{
        data: DetailsData;
        languageCode?: string;
    }>(),
    {
        resourceDescriptors: () => ({
            en: { name: 'Undefined', map_popup: '', description: '' },
        }),
        languageCode: 'en',
    },
);

type Cache = Record<string, SiteVisitSchema | null>;
const cache = ref<Cache>({});
const current = ref<SiteVisitSchema | null>(null);
const loading = ref(true);

watchEffect(async () => {
    const resourceId: string = props.data?.resourceinstance_id;
    if (!resourceId) return;
    if (!(resourceId in cache.value)) {
        getResourceData('site_visit', resourceId).then((data) => {
            cache.value[resourceId] = data as SiteVisitSchema;
            current.value = cache.value[resourceId];
            loading.value = false;
        });
    }
});
</script>

<template>
    <!-- Hack to ensure DataTable styles register -->
    <div style="display: none"><DataTable /></div>
    <div style="display: none">
        <DetailsSection
            :visible="true"
            section-title=""
        />
    </div>
    <div class="container">
        <Section1
            :data="current || undefined"
            :loading="loading"
        />
        <Section2
            :data="current || undefined"
            :loading="loading"
        />
        <Section3
            :data="current || undefined"
            :loading="loading"
        />
        <Section4
            :data="current || undefined"
            :loading="loading"
        />
        <Section5
            :data="current || undefined"
            :loading="loading"
        />
        <Section6
            :data="current || undefined"
            :loading="loading"
        />
    </div>
</template>

<style>
.container {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}
.report-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
}
.report-title {
    font-size: 1.5rem;
    font-weight: 600;
}
dl {
    display: flex;
    flex-direction: column;
    padding-bottom: 1rem;
}
dt {
    min-width: 20rem;
}
</style>
<style scoped></style>
