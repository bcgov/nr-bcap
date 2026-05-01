<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import Panel from 'primevue/panel';
import Fluid from 'primevue/fluid';
import ProgressSpinner from 'primevue/progressspinner';
import ProjectCard from '@/bcgov_arches_common/components/card/ProjectCard.vue';
import SortingBar from './SortingBar.vue';
import mockProjectsData from './mockData.json';

interface ProjectData {
    id: string;
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

// Maps raw data to the generic ProjectData interface
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const mapToDashboardCard = (rawItem: any): ProjectData => {
    return {
        id: rawItem.id,
        capPriority: rawItem.capPriority || false,
        capLabel: rawItem.capLabel || 'Unknown Process',
        capDate: rawItem.capDate || '',

        icon: rawItem.icon || 'fa-solid fa-file',
        bodyTitle: rawItem.projectName || rawItem.name || 'Untitled',
        bodySubtitle1:
            rawItem.projectId || rawItem.submissionNumber || 'Pending',
        bodySubtitle2: rawItem.bodySubtitle2 || rawItem.sector || '',

        // Passthrough the rest
        body1: rawItem.body1 || '',
        body2: rawItem.body2 || '',
        body3: rawItem.body3 || '',
        body4: rawItem.body4 || '',
        body5: rawItem.body5 || '',

        footerDate: rawItem.footerDate || new Date().toISOString(),
        footerName: rawItem.footerName || '',
        route: rawItem.route || 'default-route',
        urgency: rawItem.urgency || '',
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

// "API" call
const fetchProjects = async () => {
    return new Promise((resolve) => {
        setTimeout(() => {
            resolve(mockProjectsData);
        }, 800);
    });
};

const rawProjects = ref<ProjectData[]>([]);
const isLoading = ref(true);
const currentFilter = ref('my_projects');
const currentSearch = ref('');
const lastUpdateDate = ref(new Date());
const userName = 'John Doe';
const currentSort = ref('default');
const sortOrder = ref<'asc' | 'desc'>('asc');

onMounted(() => {
    loadData();
});

const loadData = async () => {
    isLoading.value = true;
    try {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const data = (await fetchProjects()) as any[];
        rawProjects.value = data.map(mapToDashboardCard);
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
    } else if (currentFilter.value === 'unassigned') {
        filtered = filtered.filter((item) => !item.footerName);
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
