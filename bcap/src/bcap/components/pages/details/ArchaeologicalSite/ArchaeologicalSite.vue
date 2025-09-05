<script setup lang="ts">
import { computed, ref, watchEffect } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";
import { getResourceData } from "@/bcap/components/pages/api.ts";
import "primeicons/primeicons.css";
import Section2 from "@/bcap/components/pages/details/ArchaeologicalSite/sections/DetailsSection2.vue";
import Section6 from "@/bcap/components/pages/details/ArchaeologicalSite/sections/DetailsSection6.vue";
import Section8 from "@/bcap/components/pages/details/ArchaeologicalSite/sections/DetailsSection8.vue";
import type { TileReference } from "@/bcap/types.ts";
import type { ArchaeologySiteSchema } from "@/bcap/schema/ArchaeologySiteSchema.ts";

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
        data: TileReference[];
        resourceDescriptors: ResourceDescriptors;
        languageCode?: string;
    }>(),
    {
        resourceDescriptors: () => ({ en: { name: "Undefined" } }),
        languageCode: "en",
    },
);
type ResourceCache = Record<string, ArchaeologySiteSchema>;

const resourceCache = ref<ResourceCache>({} as ResourceCache);
const currentData = ref<ArchaeologySiteSchema>({} as ArchaeologySiteSchema);
watchEffect(async () => {
    const resourceId: string = props.data?.[0]?.resourceinstance_id;
    resourceCache.value[resourceId] = await getResourceData(
        "archaeological_site",
        resourceId,
    );
    currentData.value = resourceCache.value[resourceId as string];
    console.log(Object.keys(resourceCache.value).length);
});

const now = ref(new Date());
</script>

<template>
    <div class="container">
        <div class="report-toolbar-preview ep-form-toolbar">
            <h4 class="report-toolbar-title">
                <span class="bc-report-title">Archaeological Site</span>
                -
                <span class="bc-report-title">
                    {{ props?.resourceDescriptors?.[props.languageCode]?.name }}
                </span>
            </h4>
            <!-- Tools -->
            <div class="ep-form-toolbar-tools mar-no flex">
                <p class="report-print-date">
                    <span data-bind="text: reportDate">{{ formattedNow }}</span>
                </p>
            </div>
        </div>
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
        <DetailsSection
            section-title="9. References & Related Documents"
            :visible="true"
        >
            <template #sectionContent>
                {{ currentData?.aliased_data?.related_documents }}
            </template>
        </DetailsSection>
    </div>
    <div v-if="currentData.aliased_data?.ancestral_remains">
        {{ Object.keys(currentData.aliased_data.ancestral_remains) }}
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
