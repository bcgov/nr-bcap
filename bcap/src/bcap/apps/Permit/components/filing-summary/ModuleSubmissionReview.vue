<script setup lang="ts">
import { reactive, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import Panel from 'primevue/panel';
import ProgressSpinner from 'primevue/progressspinner';
import Step99_Review from '@/bcap/apps/Permit/Modules/Step99_Review.vue';
import { fetchResourceData } from '@/bcap/apps/Permit/api.ts';
import { routeNames } from '@/bcap/apps/Permit/routes.ts';
import PermitHeaderBand from '@/bcap/apps/Permit/components/filing-summary/PermitHeaderBand.vue';
import { getReviewNav } from '@/bcap/apps/Permit/reviewNav.ts';
import type { ArchesDraftData } from '@/bcap/types.ts';

const router = useRouter();
const nav = getReviewNav();
const title = nav?.title || 'Submission';

const backLink = computed(() =>
    nav?.permitId
        ? { name: routeNames.permitDetails, params: { id: nav.permitId } }
        : { name: routeNames.home },
);

const header = nav?.permitHeader;

const state = reactive({
    loading: true,
    data: null as ArchesDraftData | null,
});

onMounted(async () => {
    // No nav means a refresh or direct hit; send them back to reopen it.
    if (!nav) {
        router.replace(backLink.value);
        return;
    }
    try {
        state.data = await fetchResourceData(nav.graph, nav.resourceId);
    } catch (error) {
        console.error('Failed to load submission:', error);
    } finally {
        state.loading = false;
    }
});
</script>

<template>
    <Panel class="full-height">
        <template
            v-if="header"
            #header
        >
            <PermitHeaderBand :header="header" />
        </template>

        <div class="review-shell">
            <RouterLink
                :to="backLink"
                class="back-link"
            >
                <i class="fa-solid fa-chevron-left"></i>
                Back to Filing Summary
            </RouterLink>

            <h1 class="review-title">Submission · {{ title }}</h1>

            <div class="review-card">
                <div
                    v-if="state.loading"
                    class="review-loading"
                >
                    <ProgressSpinner />
                </div>
                <Step99_Review
                    v-else
                    :is-submitted-view="true"
                    :resource-data="state.data"
                />
            </div>
        </div>
    </Panel>
</template>

<style scoped>
.full-height :deep(.p-panel-header) {
    padding: 0;
    border: none;
    border-radius: 0;
    background: transparent;
}

.review-shell {
    max-width: 920px;
    margin: 0 auto;
    padding: 1.5rem 1rem 3rem;
    font-family: 'BCSans', 'Noto Sans', Verdana, Arial, sans-serif;
}
.back-link {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    color: var(--bc-navy, #003366);
    font-weight: 700;
    text-decoration: none;
}
.back-link:hover {
    color: #1a5a96;
}
.review-title {
    margin: 1.25rem 0 1.5rem;
    font-size: 2.8rem;
    font-weight: 700;
    color: #26292e;
}
.review-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    box-shadow: 0 1px 3px rgba(16, 24, 40, 0.06);
    padding: 2rem 2.25rem;
}
.review-card :deep(.review-fieldset) {
    margin: 0;
}
.review-card :deep(.p-fieldset) {
    border: none;
    background: transparent;
}
.review-card :deep(.p-fieldset-content) {
    padding: 0;
}
.review-card :deep(.div-grid-cols) {
    gap: 0;
}
.review-card :deep(.div-grid-cols dt),
.review-card :deep(.div-grid-cols dd) {
    padding: 0.95rem 0;
    border-top: 1px solid #eef0f3;
    font-size: 1.25rem;
}
.review-card :deep(.div-grid-cols dt:first-of-type),
.review-card :deep(.div-grid-cols dd:nth-of-type(1)) {
    border-top: none;
}
.review-loading {
    display: flex;
    justify-content: center;
    padding: 3rem;
}
</style>
