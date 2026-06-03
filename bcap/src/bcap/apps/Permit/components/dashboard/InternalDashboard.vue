<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import Panel from 'primevue/panel';
import Fluid from 'primevue/fluid';
import ProgressSpinner from 'primevue/progressspinner';
import ProjectCard from '@/bcgov_arches_common/components/card/ProjectCard.vue';
import SortingBar from './SortingBar.vue';
import { z } from 'zod';
import { zDashboardCard } from '@/bcap/client/zod.gen';
import { getInternalDashboardData } from '@/bcap/components/pages/api.ts';
import arches from 'arches';

const currentRoute = useRoute();

interface ProjectData {
    id: string;
    reqId?: string;
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

// Extract the new types directly from the generated Zod backend schema
type GeneratedDashboardCard = z.infer<typeof zDashboardCard>;

// Maps backend JSON directly to the Dashboard Card
const mapToDashboardCard = (rawItem: GeneratedDashboardCard): ProjectData => {
    const safeUrgency = rawItem.urgency ?? 0;
    const isPriority = rawItem.priority_level === 'High' || false;

    return {
        id: rawItem.id,
        reqId: rawItem.requirement_id || rawItem.id,

        // Cap
        capPriority: isPriority,
        capLabel: rawItem.requirement_name || '',
        capDate: rawItem.requirement_due_date || 'Pending',

        // Title & Subtitles
        icon: 'fa-solid fa-folder-open',
        bodyTitle: rawItem.project_name || 'Unknown Project',
        bodySubtitle1: rawItem.application_number || 'No App #',
        bodySubtitle2: rawItem.industrial_sector || 'Sector',

        // Body
        body1: rawItem.permit_number
            ? `Permit: ${rawItem.permit_number}`
            : undefined,
        body2: rawItem.permit_holder
            ? `Holder: ${rawItem.permit_holder}`
            : undefined,
        body3: `Officer: ${rawItem.project_officer || ''}`,
        body4: undefined,
        body5: undefined,

        // Footer
        footerDate: rawItem.requirement_due_date || 'Not Started',
        footerName: rawItem.ministry_assignee_name || 'Unassigned',

        route: (currentRoute.name as string) || 'Home',
        urgency: safeUrgency,
    };
};

// Sorting options array
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

const rawProjects = ref<ProjectData[]>([]);
const isLoading = ref(true);
const currentFilter = ref('my_projects');
const currentSearch = ref('');
const lastUpdateDate = ref(new Date());
const userName = 'John Doe';
const currentSort = ref('default');
const sortOrder = ref<'asc' | 'desc'>('asc');
const page = ref(1);
const pageLimit = ref(100);
const UNASSIGNED = 'unassigned';

onMounted(() => {
    loadData();
});

watch(currentFilter, (value, oldValue) => {
    if (value !== oldValue) loadData();
});

const loadData = async () => {
    isLoading.value = true;
    try {
        const data = await getInternalDashboardData(
            currentFilter.value === UNASSIGNED,
            page.value,
            pageLimit.value,
        );
        const cards = data as GeneratedDashboardCard[];
        rawProjects.value = cards.map((item) => mapToDashboardCard(item));
        lastUpdateDate.value = new Date();
    } catch (error) {
        console.error('Error fetching projects:', error);
    } finally {
        isLoading.value = false;
    }
};

function handleSearch(searchTerm: string) {
    currentSearch.value = searchTerm;
}

const displayedProjects = computed(() => {
    let filtered = rawProjects.value;

    if (currentFilter.value === 'my_projects') {
        filtered = filtered.filter((item) => item.footerName === userName);
    } else if (currentFilter.value === UNASSIGNED) {
        filtered = filtered.filter((item) => item.footerName === 'Unassigned');
    }

    if (currentSearch.value) {
        const query = currentSearch.value.toLowerCase().trim();

        filtered = filtered.filter((item) => {
            // Special keyword If they search "priority", show all starred cards
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
        const field = currentSort.value;

        // The complex default sort (Priority -> Urgency -> Date)
        if (field === 'default') {
            if (a.capPriority !== b.capPriority) return a.capPriority ? -1 : 1;

            // Primary sort urgency level
            if (b.urgency !== a.urgency) return b.urgency - a.urgency;

            // Secondary sort cap date
            const dateA = new Date(a.capDate).getTime();
            const dateB = new Date(b.capDate).getTime();
            return (isNaN(dateA) ? 0 : dateA) - (isNaN(dateB) ? 0 : dateB);
        }

        // Date sorting (Due Date & Created Date)
        if (field === 'capDate' || field === 'footerDate') {
            const valA = a[field as 'capDate' | 'footerDate'];
            const valB = b[field as 'capDate' | 'footerDate'];

            const dateA = new Date(valA || '').getTime();
            const dateB = new Date(valB || '').getTime();

            if (isNaN(dateA) && isNaN(dateB)) return 0;
            if (isNaN(dateA)) return 1;
            if (isNaN(dateB)) return -1;
            return dateA - dateB; // Ascending (oldest first)
        }

        // Boolean sorting (Priority)
        if (field === 'capPriority') {
            return a.capPriority === b.capPriority ? 0 : a.capPriority ? -1 : 1;
        }

        // String sorting for everything else (Alphabetical Ascending)
        const valA = (a[field as keyof typeof a] || '')
            .toString()
            .toLowerCase();
        const valB = (b[field as keyof typeof b] || '')
            .toString()
            .toLowerCase();

        return valA.localeCompare(valB);
    });

    return sortOrder.value === 'desc' ? sorted.reverse() : sorted;
});

// Formats the raw API data into HTML before passing it to the card
const formatBodyLine = (text?: string) => {
    if (!text) return '';
    const parts = text.split(':');
    if (parts.length > 1) {
        const label = parts.shift();
        return `<strong>${label}:</strong>${parts.join(':')}`;
    }
    return text;
};

const navigateToReport = (item: ProjectData) => {
    window.open(
        `${arches.urls.plugin('internal-permit-dashboard')}/checklist?id=${item.reqId}`,
        item.reqId,
    );
};
</script>

<template>
    <Panel class="full-height">
        <Fluid>
            <SortingBar
                :active-tab="currentFilter"
                :last-updated="lastUpdateDate"
                :sort-options="sortOptions"
                :current-sort="currentSort"
                :sort-order="sortOrder"
                @update:sort-order="sortOrder = $event"
                @update:active-tab="currentFilter = $event"
                @update:search="handleSearch"
                @update:current-sort="currentSort = $event"
                @refresh="loadData"
            />

            <div
                v-if="!isLoading"
                class="results-summary"
            >
                Showing
                <strong>{{ displayedProjects.length }}</strong>
                of
                <strong>{{ rawProjects.length }}</strong>
                projects
                <span
                    v-if="currentSearch"
                    class="active-search-label"
                >
                    (filtered by "{{ currentSearch }}")
                </span>
            </div>

            <div
                v-if="isLoading"
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
                    :body1="formatBodyLine(item.body1)"
                    :body2="formatBodyLine(item.body2)"
                    :body3="formatBodyLine(item.body3)"
                    :body4="formatBodyLine(item.body4)"
                    :body5="formatBodyLine(item.body5)"
                    :route="{ name: item.route }"
                    :search-query="currentSearch"
                    @click.capture.prevent="navigateToReport(item)"
                />
            </div>

            <div
                v-if="!isLoading && displayedProjects.length === 0"
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
