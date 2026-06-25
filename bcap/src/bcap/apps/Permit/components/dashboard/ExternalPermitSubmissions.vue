<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import Panel from 'primevue/panel';
import Fluid from 'primevue/fluid';
import { useGettext } from 'vue3-gettext';
import Card from '@/bcgov_arches_common/components/card/CenterCard.vue';
import SortingBar from './SortingBar.vue';
import { fetchDrafts, fetchMyProjects } from '@/bcap/apps/Permit/api.ts';
import ProjectCard from '@/bcgov_arches_common/components/card/ProjectCard.vue';
import { routeNames } from '@/bcap/apps/Permit/routes.ts';

const { $gettext } = useGettext();
const router = useRouter();
const savedDrafts = ref<ResourceDraft[]>([]);
const submittedProjects = ref<DashboardProject[]>([]);

interface DashboardProject {
    id: string;
    is_draft: boolean;
    status: string;
    created_by_name: string;
    created_date: string;
    project_name: string;
    application_number: string;
    industrial_sector: string;
    permit_id: string | null;
    permit_number: string;
    urgency: number;
    priority_level: string;
}

// SortingBar State
const activeTab = ref('drafts');
const searchQuery = ref('');
const currentSort = ref('default');
const sortOrder = ref<'asc' | 'desc'>('desc');
const lastUpdated = ref(new Date());

const sortOptions = [
    { label: 'Name', value: 'name' },
    { label: 'Date Updated', value: 'updated' },
    { label: 'Date Created', value: 'created' },
];

const dashboardTabs = [
    { label: 'My Projects', value: 'my_projects' },
    { label: 'Company Projects', value: 'company_projects' },
    { label: 'Drafts', value: 'drafts' },
];

interface ResourceDraft {
    id: string;
    created: string;
    updated: string;
    data: {
        application_identification?: {
            aliased_data?: {
                project_name?: {
                    display_value: string;
                    [key: string]: unknown;
                };
            };
        };
        [key: string]: unknown;
    };
}

const workflowItems = ref([
    {
        id: 'base-module',
        label: $gettext('Submit New Application'),
        description: $gettext('New HCA Permit Application'),
        subtitle: $gettext('Start a new HCA Permit Application'),
        icon: 'fa fa-file-circle-plus',
        class: 'dashboard-card ipa',
        routeName: routeNames.baseModule,
    },
]);

const loadDashboardData = async () => {
    const [draftsData, projectsData] = await Promise.all([
        fetchDrafts(),
        fetchMyProjects(),
    ]);

    savedDrafts.value = draftsData;
    submittedProjects.value = projectsData;
    lastUpdated.value = new Date();
};

onMounted(() => {
    loadDashboardData();
});

const filteredDrafts = computed(() => {
    if (!searchQuery.value) return savedDrafts.value;
    const lowerQuery = searchQuery.value.toLowerCase();

    return savedDrafts.value.filter((draft) => {
        const title =
            draft.data?.application_identification?.aliased_data?.project_name
                ?.display_value || 'Untitled Application';
        return title.toLowerCase().includes(lowerQuery);
    });
});

const filteredProjects = computed(() => {
    if (!searchQuery.value) return submittedProjects.value;
    const lowerQuery = searchQuery.value.toLowerCase();

    return submittedProjects.value.filter((project) => {
        const title = project.project_name || 'Untitled Application';
        return title.toLowerCase().includes(lowerQuery);
    });
});

const openResourceReport = (resourceId: string) => {
    router.push({
        name: routeNames.permitDetails,
        params: { id: resourceId },
    });
};
</script>

<template>
    <Panel
        header="Start New Workflow"
        class="full-height"
        style="margin-bottom: 2rem"
    >
        <Fluid>
            <div class="dashboard-div-flex">
                <Card
                    v-for="item in workflowItems"
                    :key="item.id"
                    :label="item.label"
                    :description="item.description"
                    :subtitle="item.subtitle"
                    :icon="item.icon"
                    :class="item.class"
                    :route="{ name: item.routeName }"
                />
            </div>
        </Fluid>
    </Panel>

    <Panel class="full-height">
        <Fluid>
            <SortingBar
                v-model:active-tab="activeTab"
                v-model:search="searchQuery"
                v-model:current-sort="currentSort"
                v-model:sort-order="sortOrder"
                :tabs="dashboardTabs"
                :last-updated="lastUpdated"
                :sort-options="sortOptions"
                @refresh="loadDashboardData"
            />

            <div class="tab-content-container">
                <div v-if="activeTab === 'my_projects'">
                    <Fluid v-if="filteredProjects.length > 0">
                        <div class="dashboard-div-flex">
                            <ProjectCard
                                v-for="project in filteredProjects"
                                :key="project.id"
                                :cap-priority="
                                    project.priority_level === 'High'
                                "
                                :cap-label="project.status || 'Submitted'"
                                :cap-date="
                                    project.created_date
                                        ? new Date(
                                              project.created_date,
                                          ).toLocaleDateString()
                                        : ''
                                "
                                icon="fa-solid fa-folder-open"
                                :body-title="
                                    project.project_name ||
                                    'Untitled Application'
                                "
                                :body-subtitle1="
                                    project.application_number || 'No App #'
                                "
                                :body-subtitle2="project.industrial_sector"
                                :body1="
                                    project.permit_number
                                        ? `<strong>Permit:</strong> ${project.permit_number}`
                                        : ''
                                "
                                :footer-date="
                                    project.created_date
                                        ? new Date(
                                              project.created_date,
                                          ).toLocaleDateString()
                                        : ''
                                "
                                :footer-name="project.created_by_name"
                                :urgency="project.urgency || 0"
                                :search-query="searchQuery"
                                @click="openResourceReport(project.id)"
                            />
                        </div>
                    </Fluid>
                    <p
                        v-else
                        class="text-muted"
                    >
                        No submitted projects found.
                    </p>
                </div>

                <div v-if="activeTab === 'company_projects'">
                    <p class="text-muted">No company projects found.</p>
                </div>

                <div v-if="activeTab === 'drafts'">
                    <Fluid v-if="filteredDrafts.length > 0">
                        <div class="dashboard-div-flex">
                            <Card
                                v-for="draft in filteredDrafts"
                                :key="draft.id"
                                :label="
                                    draft.data?.application_identification
                                        ?.aliased_data?.project_name
                                        ?.display_value ||
                                    'Untitled Application'
                                "
                                description="Permit Application Draft"
                                :subtitle="`Last updated: ${new Date(draft.updated || draft.created).toLocaleDateString()}`"
                                icon="fa fa-file-pen"
                                class="dashboard-card ipa"
                                :route="{
                                    name: routeNames.baseModule,
                                    query: { draftId: draft.id },
                                }"
                            />
                        </div>
                    </Fluid>
                    <p
                        v-else
                        class="text-muted"
                    >
                        No in-progress drafts found.
                    </p>
                </div>
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
    padding-top: 1rem;
}

.dashboard-card {
    width: 225px !important;
    aspect-ratio: 1 / 1;
}

.tab-content-container {
    padding: 1rem 0;
    min-height: 300px;
}

.text-muted {
    color: #6c757d;
    font-style: italic;
    padding: 1rem 0;
}

:deep(.bcgov-custom-card) {
    height: 100%;
}

:deep(.stack-icon) {
    font-size: 4.5rem !important;
    margin-bottom: 4rem !important;
}

:deep(.bcgov-card-header) {
    font-size: 1.2rem !important;
    font-weight: 600 !important;
    line-height: 1.2 !important;
}

:deep(.description) {
    font-size: 1.15rem !important;
    font-weight: bold !important;
    color: #3b3bff !important;
}

:deep(.subtitle) {
    color: #1a1a1a !important;
    font-size: 0.95rem !important;
}
</style>
