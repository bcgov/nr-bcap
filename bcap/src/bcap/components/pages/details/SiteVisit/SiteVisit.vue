<script setup lang="ts">
import { ref, computed, watchEffect } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";
import { getResourceData } from "@/bcap/components/pages/api.ts";
import "primeicons/primeicons.css";
import Section1 from "./sections/Section1.vue";
import Section2 from "./sections/Section2.vue";
import Section3 from "./sections/Section3.vue";
import Section4 from "./sections/Section4.vue";
import Section5 from "./sections/Section5.vue";
import Section6 from "./sections/Section6.vue";
import DataTable from "primevue/datatable";
import type { DetailsData } from "@/bcap/types.ts";
import type { SiteVisitSchema } from "@/bcap/schema/SiteVisitSchema.ts";

const props = withDefaults(
    defineProps<{
        data: DetailsData;
        languageCode?: string;
    }>(),
    {
        resourceDescriptors: () => ({
            en: { name: "Undefined", map_popup: "", description: "" },
        }),
        languageCode: "en",
    },
);

type Cache = Record<string, SiteVisitSchema | null>;
const cache = ref<Cache>({});
const current = ref<SiteVisitSchema | null>(null);

watchEffect(async () => {
    const resourceId: string = props.data?.resourceinstance_id;
    if (!resourceId) return;
    if (!(resourceId in cache.value)) {
        cache.value[resourceId] = (await getResourceData(
            "site_visit",
            resourceId,
        )) as SiteVisitSchema;
    }
    current.value = cache.value[resourceId];
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
        <Section1 :data="current || undefined" />
        <Section2 :data="current || undefined" />
        <Section3 :data="current || undefined" />
        <Section4 :data="current || undefined" />
        <Section5 :data="current || undefined" />
        <Section6 :data="current || undefined" />
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
