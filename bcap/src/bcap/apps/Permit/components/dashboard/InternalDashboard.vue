<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import Panel from 'primevue/panel';
import Fluid from 'primevue/fluid';
import ProgressSpinner from 'primevue/progressspinner';
import ProjectCard from '@/bcgov_arches_common/components/card/ProjectCard.vue';
import SortingBar from './SortingBar.vue';
// import mockProjectsData from './mockData2.json';

// Grab the current route name so the cards always have a valid destination
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

interface RawRequirementData {
    resourceinstanceid: string;
    resourceinstance_id?: string; // <-- Add this
    id?: string;
    displayname: string;
    displaydescription?: string;
    graph_id: string;
    tiles: Record<string, unknown>[];
    display_values: Record<string, unknown>;
}

interface RawApplicationData {
    resourceinstanceid: string;
    displayname: string;
    displaydescription?: string;
    graph_id: string;
    tiles: Record<string, unknown>[];
    display_values: Record<string, unknown>;
    nested_process_requirements?: RawRequirementData[];
}

// Maps the backend nested JSON to the Dashboard Card interface still needs work
// Removed the unused 'index' parameter
const mapToDashboardCard = (rawItem: RawApplicationData): ProjectData[] => {
    if (
        !rawItem.nested_process_requirements ||
        rawItem.nested_process_requirements.length === 0
    ) {
        return [];
    }

    const vals = rawItem.display_values || {};

    const appId = vals['Application ID']
        ? String(vals['Application ID'])
        : 'Unknown App ID';

    const projectName = vals['Project Name']
        ? String(vals['Project Name'])
        : rawItem.displayname;

    const assignee = vals['Ministry Assignee']
        ? String(vals['Ministry Assignee'])
        : 'Unassigned';

    // Parse Urgency as a number, defaulting to 0 if blank
    const rawPriority = vals['Application Priority Level'];
    const urgencyLevel = rawPriority
        ? parseInt(String(rawPriority), 10) || 0
        : 0;

    return rawItem.nested_process_requirements.map((req) => {
        const reqVals = req.display_values || {};

        const reqNameDisplay = reqVals['Requirement Name']
            ? String(reqVals['Requirement Name'])
            : req.displayname;

        const dueDate = reqVals['Process Due Date']
            ? String(reqVals['Process Due Date'])
            : 'Due date';

        const startDate = reqVals['Process Start Date']
            ? String(reqVals['Process Start Date'])
            : 'Not Started';

        const targetReqId =
            req.resourceinstanceid || req.resourceinstance_id || req.id;

        return {
            id: `${rawItem.resourceinstanceid}-${targetReqId}`,
            reqId: targetReqId,

            capPriority: false,

            // From Process Requirement
            capLabel: reqNameDisplay,
            capDate: dueDate,
            icon: 'fa-solid fa-list-check',

            // From Permit Application
            bodyTitle: projectName,
            bodySubtitle1: appId,
            bodySubtitle2: 'Sector',

            // Dummy values waiting for the Related Permit linking
            body1: 'Permit Type: permit type',
            body2: 'Permit: 00000-0000',
            body3: 'Permit Holder: permit holder',
            body4: '',
            body5: '',

            // Mixed footer info
            footerDate: startDate,
            footerName: assignee !== 'Unassigned' ? assignee : 'John Doe',
            route: (currentRoute.name as string) || 'Home',

            urgency: urgencyLevel,
        };
    });
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

// backend API call
const fetchProjects = async () => {
    try {
        const apiUrl = '/bcap/api/dashboard';
        const response = await fetch(apiUrl);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data as RawApplicationData[];
    } catch (error) {
        console.error('Error fetching projects from backend:', error);
        return [];
    }
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
        const data = await fetchProjects();
        rawProjects.value = data.flatMap((item) => mapToDashboardCard(item));
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

const navigateToReport = (item: ProjectData) => {
    window.location.href = `/bcap/plugins/internal-permit-dashboard/checklist?id=${item.reqId}`;
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
