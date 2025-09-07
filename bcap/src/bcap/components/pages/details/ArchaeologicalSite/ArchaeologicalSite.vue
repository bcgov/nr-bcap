<script setup lang="ts">
import { ref, watchEffect } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";
import {
    getRelatedResourceData,
    getResourceData,
} from "@/bcap/components/pages/api.ts";
import "primeicons/primeicons.css";
import Section1 from "@/bcap/components/pages/details/ArchaeologicalSite/sections/DetailsSection1.vue";
import Section2 from "@/bcap/components/pages/details/ArchaeologicalSite/sections/DetailsSection2.vue";
import Section3 from "@/bcap/components/pages/details/ArchaeologicalSite/sections/DetailsSection3.vue";
import Section6 from "@/bcap/components/pages/details/ArchaeologicalSite/sections/DetailsSection6.vue";
import Section8 from "@/bcap/components/pages/details/ArchaeologicalSite/sections/DetailsSection8.vue";
import Section9 from "@/bcap/components/pages/details/ArchaeologicalSite/sections/DetailsSection9.vue";
import type { DetailsData } from "@/bcap/types.ts";
import type { ArchaeologySiteSchema } from "@/bcap/schema/ArchaeologySiteSchema.ts";

import DataTable from "primevue/datatable";
import type { SiteVisitSchema } from "@/bcap/schema/SiteVisitSchema.ts";
import type { HriaDiscontinuedDataSchema } from "@/bcap/schema/HriaDiscontinuedDataSchema.ts";

type LangCode = string;
interface Descriptor {
    name: string;
    // add more fields if needed
}

type ResourceDescriptors = Record<LangCode, Descriptor>;

const props = withDefaults(
    defineProps<{
        data: DetailsData;
        resourceDescriptors?: ResourceDescriptors;
        languageCode?: string;
    }>(),
    {
        resourceDescriptors: () => ({ en: { name: "Undefined" } }),
        languageCode: "en",
    },
);
type SiteDataCache = {
    site: ArchaeologySiteSchema | null;
    hria_discontinued_data: HriaDiscontinuedDataSchema | null;
    site_visits: SiteVisitSchema[];
};
type ResourceCache = Record<string, SiteDataCache>;

const resourceCache = ref<ResourceCache>({} as ResourceCache);
const currentData = ref<ArchaeologySiteSchema>({} as ArchaeologySiteSchema);
const siteVisitData = ref<SiteVisitSchema[]>({} as SiteVisitSchema[]);
const hriaDiscontinuedData = ref<HriaDiscontinuedDataSchema>(
    {} as HriaDiscontinuedDataSchema,
);

const siteDataLoading = ref(true);
const siteVisitDataLoading = ref(true);
const hriaDataLoading = ref(true);

watchEffect(async () => {
    const resourceId: string = props.data?.resourceinstance_id;
    if (!(resourceId in resourceCache.value)) {
        resourceCache.value[resourceId] = {
            site: null,
            hria_discontinued_data: null,
            site_visits: [],
        };
    }

    getResourceData("archaeological_site", resourceId).then((data) => {
        resourceCache.value[resourceId].site = data as ArchaeologySiteSchema;
        currentData.value = (data ?? {}) as ArchaeologySiteSchema;
        siteDataLoading.value = false;
    });

    getRelatedResourceData("site_visit", resourceId).then((data) => {
        resourceCache.value[resourceId].site_visits = data as SiteVisitSchema[];
        siteVisitData.value = data as SiteVisitSchema[];
        siteVisitDataLoading.value = false;
    });

    getRelatedResourceData("hria_discontinued_data", resourceId).then(
        (data) => {
            const hriaData: HriaDiscontinuedDataSchema =
                data && data.length > 0
                    ? (data[0] as HriaDiscontinuedDataSchema)
                    : ({} as HriaDiscontinuedDataSchema);
            resourceCache.value[resourceId].hria_discontinued_data = hriaData;
            hriaDiscontinuedData.value = hriaData;
            hriaDataLoading.value = false;
        },
    );

    console.log(Object.keys(resourceCache.value).length);
});
</script>

<template>
    <!-- Hack to ensure styles come through -->
    <div style="display: none">
        <DataTable></DataTable>
        <DetailsSection
            section-title=""
            :visible="false"
        ></DetailsSection>
    </div>
    <div class="container">
        <Section1
            :data="currentData"
            :loading="siteDataLoading"
        ></Section1>
        <Section2
            :data="currentData.aliased_data?.identification_and_registration"
            :hria-data="hriaDiscontinuedData"
            :loading="siteDataLoading"
        ></Section2>

        <Section3
            :data="siteVisitData"
            :loading="siteVisitDataLoading"
        ></Section3>
        <DetailsSection
            section-title="4. Location"
            :visible="true"
        >
            <template #sectionContent></template>
        </DetailsSection>
        <DetailsSection
            section-title="5. Site Boundary"
            :visible="true"
        >
            <template #sectionContent></template>
        </DetailsSection>
        <Section6
            :data="currentData?.aliased_data?.archaeological_data"
            :loading="siteDataLoading"
        ></Section6>
        <DetailsSection
            section-title="7. Ancestral Remains"
            :visible="true"
            :loading="siteDataLoading"
        >
            <template #sectionContent>
                {{ currentData?.aliased_data?.ancestral_remains }}
            </template>
        </DetailsSection>
        <Section8
            :data="
                currentData?.aliased_data?.remarks_and_restricted_information
            "
            :loading="siteDataLoading"
        ></Section8>
        <Section9
            :data="currentData?.aliased_data?.related_documents"
            :loading="siteDataLoading"
        ></Section9>
    </div>
    <div>
        <pre v-if="currentData.aliased_data">
            {{ Object.keys(currentData?.aliased_data) }}
        </pre>
    </div>
</template>

<style>
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
<style scoped></style>
