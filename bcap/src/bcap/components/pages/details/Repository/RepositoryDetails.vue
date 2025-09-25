<script setup lang="ts">
import { computed } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import { useResourceData } from '@/bcap/composables/useResourceData.ts';
import 'primeicons/primeicons.css';
import Section1 from '@/bcap/components/pages/details/Repository/sections/DetailsSection1.vue';
import DataTable from 'primevue/datatable';
import type { DetailsData } from '@/bcap/types.ts';
import type { RepositorySchema } from '@/bcap/schema/RepositorySchema.ts';

const props = withDefaults(
    defineProps<{
        data: DetailsData;
        languageCode?: string;
        forceCollapsed?: boolean | undefined;
    }>(),
    {
        languageCode: 'en',
        forceCollapsed: undefined,
    },
);

const resourceId = computed(() => props.data?.resourceinstance_id);
const { data: current, loading } = useResourceData<RepositorySchema>(
    'repository',
    resourceId,
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
