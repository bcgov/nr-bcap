<script setup lang="ts">
import { computed } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import {
    useResourceData,
    useRelatedResourceData,
} from '@/bcap/composables/useResourceData.ts';
import 'primeicons/primeicons.css';
import Section1 from '@/bcap/components/pages/details/ArchaeologicalSite/sections/DetailsSection1.vue';
import Section2 from '@/bcap/components/pages/details/ArchaeologicalSite/sections/DetailsSection2.vue';
import Section3 from '@/bcap/components/pages/details/ArchaeologicalSite/sections/DetailsSection3.vue';
import Section4 from '@/bcap/components/pages/details/ArchaeologicalSite/sections/DetailsSection4.vue';
import Section5 from '@/bcap/components/pages/details/ArchaeologicalSite/sections/DetailsSection5.vue';
import Section6 from '@/bcap/components/pages/details/ArchaeologicalSite/sections/DetailsSection6.vue';
import Section7 from '@/bcap/components/pages/details/ArchaeologicalSite/sections/DetailsSection7.vue';
import Section8 from '@/bcap/components/pages/details/ArchaeologicalSite/sections/DetailsSection8.vue';
import Section9 from '@/bcap/components/pages/details/ArchaeologicalSite/sections/DetailsSection9.vue';
import type { DetailsData } from '@/bcap/types.ts';
import type { ArchaeologySiteSchema } from '@/bcap/schema/ArchaeologySiteSchema.ts';
import type { SiteVisitSchema } from '@/bcap/schema/SiteVisitSchema.ts';
import type { HriaDiscontinuedDataSchema } from '@/bcap/schema/HriaDiscontinuedDataSchema.ts';
import type { SiteLocationTile } from '@/bcap/schema/ArchaeologySiteSchema.ts';
import DataTable from 'primevue/datatable';

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

const { data: currentData, loading: siteDataLoading } =
    useResourceData<ArchaeologySiteSchema>('archaeological_site', resourceId);

const { data: siteVisitData, loading: siteVisitDataLoading } =
    useRelatedResourceData<SiteVisitSchema>('site_visit', resourceId);

const { data: hriaDiscontinuedData, loading: hriaDataLoading } =
    useRelatedResourceData<HriaDiscontinuedDataSchema>(
        'hria_discontinued_data',
        resourceId,
        true,
    );

const typedCurrentData = computed(
    () => currentData.value as ArchaeologySiteSchema | undefined,
);

const typedSiteVisitData = computed(
    () => (siteVisitData.value || []) as SiteVisitSchema[],
);

const typedHriaData = computed(
    () => hriaDiscontinuedData.value as HriaDiscontinuedDataSchema | undefined,
);
</script>

<template>
    <div style="display: none">
        <DataTable></DataTable>
        <DetailsSection
            section-title=""
            :visible="false"
        ></DetailsSection>
    </div>

    <div class="container">
        <Section1
            :data="typedCurrentData"
            :loading="siteDataLoading"
            :force-collapsed="props.forceCollapsed"
        />
        <Section2
            :data="
                typedCurrentData?.aliased_data?.identification_and_registration
            "
            :hria-data="typedHriaData"
            :loading="siteDataLoading"
            :force-collapsed="props.forceCollapsed"
            :edit-log-data="props.editLogData"
        />
        <Section3
            :data="typedSiteVisitData"
            :loading="siteVisitDataLoading"
            :force-collapsed="props.forceCollapsed"
            :edit-log-data="props.editLogData"
        />
        <Section4
            :data="
                (typedCurrentData?.aliased_data
                    ?.heritage_site_location?.[0] as SiteLocationTile) ||
                undefined
            "
            :site-visit-data="typedSiteVisitData"
            :hria-data="typedHriaData"
            :loading="siteDataLoading"
            :force-collapsed="props.forceCollapsed"
            :edit-log-data="props.editLogData"
        />
        <Section5
            :data="typedCurrentData?.aliased_data?.site_boundary"
            :hria-data="typedHriaData"
            :loading="siteDataLoading || hriaDataLoading"
            :force-collapsed="props.forceCollapsed"
            :edit-log-data="props.editLogData"
        />
        <Section6
            :data="typedCurrentData?.aliased_data?.archaeological_data"
            :loading="siteDataLoading"
            :force-collapsed="props.forceCollapsed"
            :edit-log-data="props.editLogData"
        />
        <Section7
            :data="typedCurrentData?.aliased_data?.ancestral_remains"
            :site-visit-data="typedSiteVisitData"
            :loading="siteDataLoading || siteVisitDataLoading"
            :force-collapsed="props.forceCollapsed"
            :edit-log-data="props.editLogData"
        />
        <Section8
            :data="
                typedCurrentData?.aliased_data
                    ?.remarks_and_restricted_information
            "
            :site-visit-data="typedSiteVisitData"
            :loading="siteDataLoading"
            :force-collapsed="props.forceCollapsed"
            :show-audit-fields="props.showAuditFields"
            :edit-log-data="props.editLogData"
        />
        <Section9
            :data="typedCurrentData?.aliased_data?.related_documents"
            :loading="siteDataLoading"
            :force-collapsed="props.forceCollapsed"
            :show-audit-fields="props.showAuditFields"
            :edit-log-data="props.editLogData"
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
    padding-top: 0.75rem;
}
</style>
