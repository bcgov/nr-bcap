<script setup lang="ts">
import { computed, ref, watchEffect } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";
import {
    getRelatedResourceData,
    getResourceData,
} from "@/bcap/components/pages/api.ts";
import "primeicons/primeicons.css";
import Section2 from "@/bcap/components/pages/details/ArchaeologicalSite/sections/DetailsSection2.vue";
import Section6 from "@/bcap/components/pages/details/ArchaeologicalSite/sections/DetailsSection6.vue";
import Section8 from "@/bcap/components/pages/details/ArchaeologicalSite/sections/DetailsSection8.vue";
import Section9 from "@/bcap/components/pages/details/ArchaeologicalSite/sections/DetailsSection9.vue";
import type { DetailsData } from "@/bcap/types.ts";
import type { ArchaeologySiteSchema } from "@/bcap/schema/ArchaeologySiteSchema.ts";

import DataTable from "primevue/datatable";
import type { SiteVisitSchema } from "@/bcap/schema/SiteVisitSchema.ts";

type LangCode = string;
interface Descriptor {
    name: string;
    // add more fields if needed
}

type ResourceDescriptors = Record<LangCode, Descriptor>;

const formattedNow = computed(() => {
    // undefined => use browser's locale (e.g., "en-CA", "fr-FR", etc.)
    return new Intl.DateTimeFormat(undefined, {
        year: "numeric",
        month: "long",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
    }).format(now.value);
});

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
    hria_discontinued_data: object | null;
    site_visits: SiteVisitSchema[];
};
type ResourceCache = Record<string, SiteDataCache>;

const resourceCache = ref<ResourceCache>({} as ResourceCache);
const currentData = ref<ArchaeologySiteSchema>({} as ArchaeologySiteSchema);
watchEffect(async () => {
    const resourceId: string = props.data?.resourceinstance_id;
    if (!(resourceId in resourceCache.value)) {
        resourceCache.value[resourceId] = {
            site: null,
            hria_discontinued_data: null,
            site_visits: [],
        };
    }
    resourceCache.value[resourceId].site = (await getResourceData(
        "archaeological_site",
        resourceId,
    )) as ArchaeologySiteSchema;

    getRelatedResourceData("site_visit", resourceId).then(
        (data) =>
            (resourceCache.value[resourceId].site_visits =
                data as SiteVisitSchema[]),
    );
    currentData.value =
        resourceCache.value[resourceId as string].site ??
        ({} as ArchaeologySiteSchema);
    console.log(Object.keys(resourceCache.value).length);
});

const now = ref(new Date());
</script>

<template>
    <!-- Hack to ensure styles come through -->
    <div style="display: none">
        <DataTable></DataTable>
    </div>
    <div class="container">
        <DetailsSection
            section-title="1. Spatial View"
            :visible="true"
        >
            <template #sectionContent>
                <div>
                    <dl>
                        <dt>Source Notes</dt>
                        <dd>
                            {{
                                currentData.aliased_data?.site_boundary
                                    ?.aliased_data.source_notes?.display_value
                            }}
                        </dd>
                        <div
                            v-if="
                                currentData.aliased_data?.site_boundary
                                    ?.aliased_data?.latest_edit_type?.node_value
                            "
                        >
                            <dt>Latest Edit Type</dt>
                            <dd>
                                {{
                                    currentData.aliased_data?.site_boundary
                                        ?.aliased_data?.latest_edit_type
                                        ?.display_value
                                }}
                            </dd>
                        </div>
                    </dl>
                </div>
            </template>
        </DetailsSection>
        <Section2
            :data="currentData.aliased_data?.identification_and_registration"
        ></Section2>
        <DetailsSection
            section-title="3. Site Visits"
            :visible="true"
        >
            <template #sectionContent></template>
        </DetailsSection>
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
        ></Section6>
        <DetailsSection
            section-title="7. Ancestral Remains"
            :visible="true"
        >
            <template #sectionContent>
                {{ currentData?.aliased_data?.ancestral_remains }}
            </template>
        </DetailsSection>
        <Section8
            :data="
                currentData?.aliased_data?.remarks_and_restricted_information
            "
        ></Section8>
        <Section9
            :data="currentData?.aliased_data?.related_documents"
        ></Section9>
    </div>
    <div>
        <pre v-if="currentData.aliased_data">
            {{ Object.keys(currentData?.aliased_data) }}
        </pre>
        {{ currentData?.aliased_data }}
        <span></span>
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
}
</style>
<style scoped></style>
