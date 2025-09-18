<script setup lang="ts">
import { ref, watchEffect } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";
import { getResourceData } from "@/bcap/components/pages/api.ts";
import "primeicons/primeicons.css";
import Section1 from "@/bcap/components/pages/details/Repository/sections/DetailsSection1.vue";
import DataTable from "primevue/datatable";
import type { DetailsData } from "@/bcap/types.ts";
import type { RepositorySchema } from "@/bcap/schema/RepositorySchema.ts";

const props = withDefaults(
    defineProps<{
        data: DetailsData;
        languageCode?: string;
    }>(),
    {
        languageCode: "en",
    },
);

type Cache = Record<string, RepositorySchema | null>;
const cache = ref<Cache>({});
const current = ref<RepositorySchema | null>(null);
const loading = ref(true);

watchEffect(async () => {
    const resourceId: string = props.data?.resourceinstance_id;
    if (!resourceId) return;
    if (!(resourceId in cache.value)) {
        getResourceData("repository", resourceId).then((data) => {
            cache.value[resourceId] = data as RepositorySchema;
            current.value = cache.value[resourceId];
            loading.value = false;
        });
    }
});
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
