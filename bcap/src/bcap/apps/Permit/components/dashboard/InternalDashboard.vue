<script setup lang="ts">
import { reactive, computed, onMounted, watch } from 'vue';
import DOMPurify from 'dompurify';
import { useRoute, useRouter } from 'vue-router';
import { routeNames } from '@/bcap/apps/Permit/routes.ts';
import Panel from 'primevue/panel';
import Fluid from 'primevue/fluid';
import ProgressSpinner from 'primevue/progressspinner';
import ProjectCard from '@/bcgov_arches_common/components/card/ProjectCard.vue';
import SortingBar from './SortingBar.vue';
import {
    getInternalDashboardData,
    type DashboardStatus,
} from '@/bcap/components/pages/api.ts';
import type { InternalDashboardCard } from '@/bcap/client/types.gen.ts';
import { buildModuleSummary } from '@/bcap/apps/Permit/moduleSummary.ts';

const currentRoute = useRoute();
const router = useRouter();

interface ProjectData {
    id: string;
    unreadMessages: number;
    capPriority: boolean;
    capLabel: string;
    capDate: string;
    icon: string;
    bodyTitle: string;
    bodySubtitle1: string;
    bodySubtitle2: string;
    body1?: string;
    body2?: string;
    body3?: string;
    body4?: string;
    body5?: string;
    footerDate: string;
    footerName?: string;
    class?: string;
    route: string;
    urgency: number;
}

const mapToDashboardCard = (rawItem: InternalDashboardCard): ProjectData => {
    const safeUrgency = rawItem.urgency ?? 0;
    const isPriority = rawItem.priority_level === 'High' || false;

    return {
        id: rawItem.id,
        unreadMessages: rawItem.unread_messages || 0,

        capPriority: isPriority,
        capLabel: rawItem.requirement_name || '',
        capDate: rawItem.requirement_due_date || 'Pending',

        icon: 'fa-solid fa-folder-open',
        bodyTitle: rawItem.project_name || 'Unknown Project',
        bodySubtitle1: rawItem.application_number || 'No App #',
        bodySubtitle2: rawItem.industrial_sector || 'Sector',

        body1: rawItem.submission_type
            ? `Type: ${rawItem.submission_type}`
            : undefined,
        body2: rawItem.permit_number
            ? `Permit: ${rawItem.permit_number}`
            : undefined,
        body3: rawItem.permit_holder
            ? `Holder: ${rawItem.permit_holder}`
            : undefined,
        body4: `Officer: ${rawItem.project_officer || ''}`,
        body5: buildModuleSummary(rawItem.module_progress),

        footerDate: rawItem.requirement_due_date || 'Not Started',
        footerName: rawItem.ministry_assignee_name || 'Unassigned',

        route: (currentRoute.name as string) || 'Home',
        urgency: safeUrgency,
    };
};

const sortOptions = [
    { label: 'Default (Urgency)', value: 'default' },
    { label: 'Application Number', value: 'bodySubtitle1' },
    { label: 'Assigned To', value: 'footerName' },
    { label: 'Created Date', value: 'footerDate' },
    { label: 'Due Date', value: 'capDate' },
    { label: 'Permit Holder', value: 'body3' },
    { label: 'Permit Number', value: 'body2' },
    { label: 'Priority', value: 'capPriority' },
    { label: 'Process', value: 'capLabel' },
    { label: 'Project Officer', value: 'body4' },
    { label: 'Sector', value: 'bodySubtitle2' },
    { label: 'Submission Type', value: 'body1' },
];

const internalTabs = [
    { label: 'My Projects', value: 'ASSIGNED_TO_ME' },
    { label: 'Unassigned', value: 'UNASSIGNED' },
    { label: 'All', value: 'ALL' },
];

const TAB_KEY = 'bcap.internalDashboard.tab';
const savedTab = sessionStorage.getItem(TAB_KEY);
const initialTab = internalTabs.some((tab) => tab.value === savedTab)
    ? (savedTab as DashboardStatus | 'ALL')
    : 'ASSIGNED_TO_ME';

const state = reactive({
    rawProjects: [] as ProjectData[],
    isLoading: true,
    currentFilter: initialTab,
    currentSearch: '',
    lastUpdateDate: new Date(),
    currentSort: 'default',
    messagesOnly: false,
    sortOrder: 'asc' as 'asc' | 'desc',
    page: 1,
    pageLimit: 100,
});

onMounted(() => {
    loadData();
});

watch(
    () => state.currentFilter,
    (value, oldValue) => {
        if (value) sessionStorage.setItem(TAB_KEY, value);
        if (value !== oldValue) loadData();
    },
);

const loadData = async () => {
    state.isLoading = true;
    try {
        const status =
            state.currentFilter === 'ALL' ? undefined : state.currentFilter;

        const response = await getInternalDashboardData(
            status,
            state.page,
            state.pageLimit,
        );

        state.rawProjects = response.map(mapToDashboardCard);
        state.lastUpdateDate = new Date();
    } catch (error) {
        console.error('Error fetching projects:', error);
    } finally {
        state.isLoading = false;
    }
};

function handleSearch(searchTerm: string) {
    state.currentSearch = searchTerm;
}

const displayedProjects = computed(() => {
    let filtered = state.rawProjects;

    if (state.messagesOnly) {
        filtered = filtered.filter((item) => item.unreadMessages > 0);
    }

    if (state.currentSearch) {
        const query = state.currentSearch.toLowerCase().trim();

        filtered = filtered.filter((item) => {
            if (query === 'priority' && item.capPriority) {
                return true;
            }

            return (
                item.capLabel?.toLowerCase().includes(query) ||
                item.bodyTitle?.toLowerCase().includes(query) ||
                item.bodySubtitle1?.toLowerCase().includes(query) ||
                item.bodySubtitle2?.toLowerCase().includes(query) ||
                item.body1?.toLowerCase().includes(query) ||
                item.body2?.toLowerCase().includes(query) ||
                item.body3?.toLowerCase().includes(query) ||
                item.body4?.toLowerCase().includes(query) ||
                item.body5?.toLowerCase().includes(query) ||
                item.footerName?.toLowerCase().includes(query)
            );
        });
    }

    // Apply Dynamic Sorting
    const sorted = filtered.slice().sort((a, b) => {
        const field = state.currentSort;

        if (field === 'default') {
            if (a.capPriority !== b.capPriority) return a.capPriority ? -1 : 1;
            if (b.urgency !== a.urgency) return b.urgency - a.urgency;

            const dateA = new Date(a.capDate).getTime();
            const dateB = new Date(b.capDate).getTime();
            return (isNaN(dateA) ? 0 : dateA) - (isNaN(dateB) ? 0 : dateB);
        }

        if (field === 'capDate' || field === 'footerDate') {
            const valA = a[field as 'capDate' | 'footerDate'];
            const valB = b[field as 'capDate' | 'footerDate'];

            const dateA = new Date(valA || '').getTime();
            const dateB = new Date(valB || '').getTime();

            if (isNaN(dateA) && isNaN(dateB)) return 0;
            if (isNaN(dateA)) return 1;
            if (isNaN(dateB)) return -1;
            return dateA - dateB;
        }

        if (field === 'capPriority') {
            return a.capPriority === b.capPriority ? 0 : a.capPriority ? -1 : 1;
        }

        const valA = (a[field as keyof typeof a] || '')
            .toString()
            .toLowerCase();
        const valB = (b[field as keyof typeof b] || '')
            .toString()
            .toLowerCase();

        return valA.localeCompare(valB);
    });

    return state.sortOrder === 'desc' ? sorted.reverse() : sorted;
});

const formatBodyLine = (text?: string) =>
    text ? DOMPurify.sanitize(text) : '';

const onCardClick = (event: MouseEvent, item: ProjectData) => {
    // Ctrl/Cmd-click opens the underlying resource instead of the permit view.
    if (event.ctrlKey || event.metaKey) {
        window.open(`/bcap/resource/${item.id}`, '_blank');
        return;
    }
    // Staff open the permit view; isStaff enables the module edit controls.
    router.push({
        name: routeNames.permitDetails,
        params: { id: item.id },
        query: { staff: 'true' },
    });
};
</script>

<template>
    <Panel class="full-height">
        <Fluid>
            <SortingBar
                v-model:active-tab="state.currentFilter"
                v-model:current-sort="state.currentSort"
                v-model:sort-order="state.sortOrder"
                v-model:messages-only="state.messagesOnly"
                :tabs="internalTabs"
                :last-updated="state.lastUpdateDate"
                :sort-options="sortOptions"
                messages-only-label="Unread messages only"
                :shown="state.isLoading ? 0 : displayedProjects.length"
                :total="state.isLoading ? 0 : state.rawProjects.length"
                @update:search="handleSearch"
                @refresh="loadData"
            />

            <div
                v-if="state.isLoading"
                class="loading-state"
            >
                <ProgressSpinner
                    style="width: 50px; height: 50px"
                    stroke-width="4"
                />
                <p>Loading projects...</p>
            </div>

            <div
                v-else
                class="dash-row"
            >
                <ProjectCard
                    v-for="item in displayedProjects"
                    :key="item.id"
                    v-bind="item"
                    :unread-messages="item.unreadMessages"
                    :body1="formatBodyLine(item.body1)"
                    :body2="formatBodyLine(item.body2)"
                    :body3="formatBodyLine(item.body3)"
                    :body4="item.body4"
                    :body5="formatBodyLine(item.body5)"
                    :route="{ name: item.route }"
                    :search-query="state.currentSearch"
                    @click.capture.prevent="onCardClick($event, item)"
                />
            </div>

            <div
                v-if="!state.isLoading && displayedProjects.length === 0"
                class="empty-state"
            >
                <p>No projects match your search criteria.</p>
            </div>
        </Fluid>
    </Panel>
    <br />
    <br />
    <br />
</template>

<style scoped>
/* The whole card is the link, so the hover underline on its title reads as
   noise here. Beats the theme's .bcgov-main-content rule on specificity. */
.full-height :deep(a:hover),
.full-height :deep(a:focus) {
    text-decoration: none;
}

.dash-row {
    display: flex;
    flex-direction: row;
    flex-wrap: wrap;
    gap: 1.5rem;
    margin: 0 -10px 1rem;
}

/* ProjectCard clamps its title to two lines with overflow:hidden at
   line-height 1.1, which is shorter than the glyphs and cuts the descenders
   off "g", "y" and friends. */
.dash-row :deep(.bodyTitle) {
    line-height: 1.35;
}

.loading-state,
.empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 3rem;
    color: #555;
}
</style>
