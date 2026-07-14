<script setup lang="ts">
import { reactive, computed, onMounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import Panel from 'primevue/panel';
import Fluid from 'primevue/fluid';
import ProgressSpinner from 'primevue/progressspinner';
import ProjectCard from '@/bcgov_arches_common/components/card/ProjectCard.vue';
import SortingBar from './SortingBar.vue';
import {
    getInternalDashboardData,
    type DashboardStatus,
    type InternalDashboardCard,
} from '@/bcap/components/pages/api.ts';

const currentRoute = useRoute();

interface ProjectData {
    id: string;
    realId: string; // Keep track of the true resource ID for routing
    permitId?: string;
    reqId?: string;
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
        realId: rawItem.id,
        permitId: rawItem.permit_id ?? undefined,
        reqId: rawItem.requirement_id || rawItem.id,
        unreadMessages: rawItem.unread_messages || 0,

        capPriority: isPriority,
        capLabel: rawItem.requirement_name || '',
        capDate: rawItem.requirement_due_date || 'Pending',

        icon: 'fa-solid fa-folder-open',
        bodyTitle: rawItem.project_name || 'Unknown Project',
        bodySubtitle1: rawItem.application_number || 'No App #',
        bodySubtitle2: rawItem.industrial_sector || 'Sector',

        body1: rawItem.permit_number
            ? `Permit: ${rawItem.permit_number}`
            : undefined,
        body2: rawItem.permit_holder
            ? `Holder: ${rawItem.permit_holder}`
            : undefined,
        body3: `Officer: ${rawItem.project_officer || ''}`,
        body4: undefined,
        body5: undefined,

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
    { label: 'Permit Holder', value: 'body2' },
    { label: 'Permit Number', value: 'body1' },
    { label: 'Priority', value: 'capPriority' },
    { label: 'Process', value: 'capLabel' },
    { label: 'Project Officer', value: 'body3' },
    { label: 'Sector', value: 'bodySubtitle2' },
];

const internalTabs = [
    { label: 'My Projects', value: 'ASSIGNED_TO_ME' },
    { label: 'Unassigned', value: 'UNASSIGNED' },
    { label: 'All', value: 'ALL' },
];

const state = reactive({
    rawProjects: [] as ProjectData[],
    isLoading: true,
    currentFilter: 'ASSIGNED_TO_ME' as DashboardStatus | 'ALL',
    currentSearch: '',
    lastUpdateDate: new Date(),
    currentSort: 'default',
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
        if (value !== oldValue) loadData();
    },
);

const loadData = async () => {
    state.isLoading = true;
    try {
        const status =
            state.currentFilter === 'ALL' ? undefined : state.currentFilter;

        const response = (await getInternalDashboardData(
            status,
            state.page,
            state.pageLimit,
        )) as unknown as
            { results?: InternalDashboardCard[] } | InternalDashboardCard[];

        const items: InternalDashboardCard[] =
            'results' in response && response.results
                ? response.results
                : (response as InternalDashboardCard[]);

        const processedCards: ProjectData[] = [];

        items.forEach((rawItem: InternalDashboardCard) => {
            processedCards.push(mapToDashboardCard(rawItem));
        });

        state.rawProjects = processedCards;
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

const formatBodyLine = (text?: string) => {
    if (!text) return '';
    const parts = text.split(':');
    if (parts.length > 1) {
        const label = parts.shift();
        return `<strong>${label}:</strong>${parts.join(':')}`;
    }
    return text;
};

const onCardClick = (event: MouseEvent, item: ProjectData) => {
    const targetId = item.permitId || item.realId;
    const targetUrl = `/bcap/plugins/external-permit-workflows/permit/${targetId}`;

    // Open in a new tab if the user holds Ctrl or Cmd, otherwise open in the current window
    if (event.ctrlKey || event.metaKey) {
        window.open(`/bcap/resource/${item.id}`, '_blank');
        return;
    } else {
        window.location.href = targetUrl;
    }
};
</script>

<template>
    <Panel class="full-height">
        <Fluid>
            <SortingBar
                v-model:active-tab="state.currentFilter"
                v-model:current-sort="state.currentSort"
                v-model:sort-order="state.sortOrder"
                :tabs="internalTabs"
                :last-updated="state.lastUpdateDate"
                :sort-options="sortOptions"
                @update:search="handleSearch"
                @refresh="loadData"
            />

            <div
                v-if="!state.isLoading"
                class="results-summary"
            >
                Showing
                <strong>{{ displayedProjects.length }}</strong>
                of
                <strong>{{ state.rawProjects.length }}</strong>
                cards
                <span
                    v-if="state.currentSearch"
                    class="active-search-label"
                >
                    (filtered by "{{ state.currentSearch }}")
                </span>
            </div>

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
                    :body4="formatBodyLine(item.body4)"
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
.dashboard-div-flex {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
}
.dash-row {
    display: flex;
    flex-direction: row;
    flex-wrap: wrap;
    gap: 1.5rem;
    margin-bottom: 1rem;
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

/* Results Counter Styling */
.results-summary {
    font-size: 1.1rem;
    color: #555555;
    margin-bottom: 1rem;
    padding-left: 0.5rem;
}

.results-summary strong {
    color: #003366;
    font-weight: 700;
}

.active-search-label {
    color: #777777;
    font-style: italic;
    margin-left: 0.5rem;
}
</style>
