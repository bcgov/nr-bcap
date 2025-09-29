<script setup lang="ts">
import { computed } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import {
    useResourceData,
    useRelatedResourceData,
} from '@/bcap/composables/useResourceData.ts';
import 'primeicons/primeicons.css';
import Section1 from '@/bcap/components/pages/details/SiteVisit/sections/SiteVisitDetailsSection1.vue';
import Section2 from '@/bcap/components/pages/details/SiteVisit/sections/SiteVisitDetailsSection2.vue';
import Section3 from '@/bcap/components/pages/details/SiteVisit/sections/SiteVisitDetailsSection3.vue';
import Section4 from '@/bcap/components/pages/details/SiteVisit/sections/SiteVisitDetailsSection4.vue';
import Section5 from '@/bcap/components/pages/details/SiteVisit/sections/SiteVisitDetailsSection5.vue';
import Section6 from '@/bcap/components/pages/details/SiteVisit/sections/SiteVisitDetailsSection6.vue';
import Section7 from '@/bcap/components/pages/details/SiteVisit/sections/SiteVisitDetailsSection7.vue';
import DataTable from 'primevue/datatable';
import type { DetailsData } from '@/bcap/types.ts';
import type { SiteVisitSchema } from '@/bcap/schema/SiteVisitSchema.ts';
import type { HriaDiscontinuedDataSchema } from '@/bcap/schema/HriaDiscontinuedDataSchema.ts';

const props = withDefaults(
    defineProps<{
        data: DetailsData;
        languageCode?: string;
        forceCollapsed?: boolean;
        editLogData?: Record<string, { entered_on: string | null; entered_by: string | null }>;
    }>(),
    {
        languageCode: 'en',
        forceCollapsed: undefined,
        editLogData: () => ({}),
    },
);

const resourceId = computed(() => props.data?.resourceinstance_id);

const { data: current, loading } = useResourceData<SiteVisitSchema>(
    'site_visit',
    resourceId,
);

const { data: hriaData } = useRelatedResourceData<HriaDiscontinuedDataSchema>(
    'hria_discontinued_data',
    resourceId,
    true,
);
</script>

<template>
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
            :force-collapsed="props.forceCollapsed"
        />
        <Section2
            :data="current || undefined"
            :loading="loading"
            :force-collapsed="props.forceCollapsed"
            :edit-log-data="props.editLogData"
        />
        <Section3
            :data="current || undefined"
            :loading="loading"
            :force-collapsed="props.forceCollapsed"
            :edit-log-data="props.editLogData"
        />
        <Section4
            :data="current || undefined"
            :hria-data="(hriaData as HriaDiscontinuedDataSchema) || undefined"
            :loading="loading"
            :force-collapsed="props.forceCollapsed"
        />
        <Section5
            :data="current || undefined"
            :loading="loading"
            :force-collapsed="props.forceCollapsed"
        />
        <Section6
            :data="current || undefined"
            :loading="loading"
            :force-collapsed="props.forceCollapsed"
            :edit-log-data="props.editLogData"
        />
        <Section7
            :data="current || undefined"
            :loading="loading"
            :force-collapsed="props.forceCollapsed"
        />
    </div>
</template>

<style>
.container {
    display: flex;
    flex-direction: column;
    gap: 1rem;
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
