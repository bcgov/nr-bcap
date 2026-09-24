<script setup lang="ts">
import { computed } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import InlineError from '@/bcap/components/InlineError.vue';
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
import type {
    SiteVisit,
    HriaDiscontinuedData,
} from '@/bcap/client/types.gen.ts';

const props = withDefaults(
    defineProps<{
        data: DetailsData;
        languageCode?: string;
        forceCollapsed?: boolean;
        editLogData?: Record<
            string,
            { entered_on: string | null; entered_by: string | null }
        >;
        showAuditFields?: boolean;
    }>(),
    {
        languageCode: 'en',
        forceCollapsed: undefined,
        editLogData: () => ({}),
        showAuditFields: false,
    },
);

const resourceId = computed(() => props.data?.resourceinstance_id);

const {
    data: current,
    loading,
    error: visitError,
} = useResourceData<SiteVisit>('site_visit', resourceId);

const { data: hriaData, error: hriaError } =
    useRelatedResourceData<HriaDiscontinuedData>(
        'hria_discontinued_data',
        resourceId,
        true,
    );

const loadError = computed(() => visitError.value || hriaError.value);
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
        <InlineError
            v-if="loadError"
            title="Some of this record could not be loaded."
            :detail="loadError"
        />
        <Section1
            :data="current || undefined"
            :loading="loading"
            :force-collapsed="props.forceCollapsed"
        />
        <Section2
            :data="current || undefined"
            :loading="loading"
            :force-collapsed="props.forceCollapsed"
            :show-audit-fields="props.showAuditFields"
            :edit-log-data="props.editLogData"
        />
        <Section3
            :data="current || undefined"
            :loading="loading"
            :force-collapsed="props.forceCollapsed"
            :show-audit-fields="props.showAuditFields"
            :edit-log-data="props.editLogData"
        />
        <Section4
            :data="current || undefined"
            :hria-data="
                (hriaData as HriaDiscontinuedData | undefined) || undefined
            "
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
            :show-audit-fields="props.showAuditFields"
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
