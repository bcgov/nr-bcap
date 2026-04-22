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
    projectName: string;
    projectId: string;
    sector?: string;
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

onMounted(async () => {
    isLoading.value = true;
    try {
        const data = await fetchProjects();
        rawProjects.value = data as ProjectData[];
    } catch (error) {
        console.error('Error fetching projects:', error);
    } finally {
        isLoading.value = false;
        loadData();
    }
});

const loadData = async () => {
    isLoading.value = true;
    try {
        const data = await fetchProjects();
        rawProjects.value = data as ProjectData[];
        // Just record the raw time of success
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
                item.projectName?.toLowerCase().includes(query) ||
                item.projectId?.toLowerCase().includes(query) ||
                item.sector?.toLowerCase().includes(query) ||
                item.body1?.toLowerCase().includes(query) ||
                item.body2?.toLowerCase().includes(query) ||
                item.body3?.toLowerCase().includes(query) ||
                item.body4?.toLowerCase().includes(query) ||
                item.body5?.toLowerCase().includes(query) ||
                item.footerName?.toLowerCase().includes(query)
            );
        });
    }

    return filtered.slice().sort((a, b) => {
        // Primary sort urgency level
        if (b.urgency !== a.urgency) {
            return b.urgency - a.urgency;
        }
        // Secondary sort cap date
        const dateA = new Date(a.capDate).getTime();
        const dateB = new Date(b.capDate).getTime();
        if (isNaN(dateA) || isNaN(dateB)) return 0;

        return dateA - dateB;
    });
});
</script>

<template>
    <Panel
        header="Workflows"
        class="full-height"
    >
        <Fluid>
            <br />
            <br />
            <br />
            <br />
            <br />
            <br />

            <SortingBar
                :active-tab="currentFilter"
                :last-updated="lastUpdateDate"
                @update:active-tab="currentFilter = $event"
                @update:search="handleSearch"
                @refresh="loadData"
            />

            <div v-if="!isLoading">
                Showing
                <strong>{{ displayedProjects.length }}</strong>
                of
                <strong>{{ rawProjects.length }}</strong>
                projects
                <span v-if="currentSearch">
                    (filtered by "{{ currentSearch }}")
                </span>
            </div>

            <div
                v-if="!isLoading"
                class="dash-row"
            ></div>

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
</style>
