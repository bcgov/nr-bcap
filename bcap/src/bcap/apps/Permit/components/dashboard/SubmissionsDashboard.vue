<script setup lang="ts">
import { ref, reactive, onMounted, computed, watch } from 'vue';
import { useRouter } from 'vue-router';
import Panel from 'primevue/panel';
import Fluid from 'primevue/fluid';
import Dialog from 'primevue/dialog';
import Button from 'primevue/button';
import ProgressSpinner from 'primevue/progressspinner';
import { useGettext } from 'vue3-gettext';
import Card from '@/bcgov_arches_common/components/card/CenterCard.vue';
import SortingBar from './SortingBar.vue';
import {
    fetchDraftCards,
    fetchMyProjects,
    deleteDraft,
} from '@/bcap/apps/Permit/api.ts';
import { buildModuleSummary } from '@/bcap/apps/Permit/moduleSummary.ts';
import { GraphSlug } from '@/bcap/apps/Permit/graphSlug.ts';
import type { ModuleProgress } from '@/bcap/client/types.gen.ts';
import ProjectCard from '@/bcgov_arches_common/components/card/ProjectCard.vue';
import { routeNames } from '@/bcap/apps/Permit/routes.ts';

const { $gettext } = useGettext();
const router = useRouter();
const savedDrafts = ref<DashboardProject[]>([]);
const submittedProjects = ref<DashboardProject[]>([]);

interface DashboardProject {
    id: string;
    is_draft: boolean;
    status: string;
    created_by_name: string;
    created_date: string;
    updated_date: string;
    project_name: string;
    application_number: string;
    submission_type: string;
    industrial_sector: string;
    permit_id: string | null;
    permit_number: string;
    urgency: number;
    priority_level: string;
    unread_messages: number;
    module_progress: ModuleProgress;
}

const EXTERNAL_TAB_KEY = 'bcap.externalDashboard.tab';
const EXTERNAL_TABS = ['my_projects', 'company_projects', 'drafts'];
const storedTab = localStorage.getItem(EXTERNAL_TAB_KEY) ?? '';
const activeTab = ref(EXTERNAL_TABS.includes(storedTab) ? storedTab : 'drafts');
watch(activeTab, (tab) => localStorage.setItem(EXTERNAL_TAB_KEY, tab));
const searchQuery = ref('');
const currentSort = ref('default');
const messagesOnly = ref(false);
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

const isLoading = ref(true);

const loadDashboardData = async () => {
    isLoading.value = true;
    try {
        const [draftsData, projectsData] = await Promise.all([
            fetchDraftCards(),
            fetchMyProjects(),
        ]);

        savedDrafts.value = draftsData;
        submittedProjects.value = projectsData;
        lastUpdated.value = new Date();
    } catch (error) {
        console.error('Failed to load dashboard data:', error);
    } finally {
        isLoading.value = false;
    }
};

onMounted(() => {
    loadDashboardData();
});

const DRAFT_LABEL = 'Permit Application Draft';

const deleteState = reactive<{
    visible: boolean;
    busy: boolean;
    draft: DashboardProject | null;
}>({ visible: false, busy: false, draft: null });

const confirmDelete = (draft: DashboardProject) => {
    deleteState.draft = draft;
    deleteState.visible = true;
};

const performDelete = async () => {
    const draft = deleteState.draft;
    if (!draft) return;
    deleteState.busy = true;
    try {
        await deleteDraft(GraphSlug.PermitApplication, draft.id);
        savedDrafts.value = savedDrafts.value.filter((d) => d.id !== draft.id);
        deleteState.visible = false;
    } catch (error) {
        console.error('Failed to delete draft:', error);
    } finally {
        deleteState.busy = false;
    }
};

const filteredDrafts = computed(() => {
    const drafts = messagesOnly.value
        ? savedDrafts.value.filter((draft) => (draft.unread_messages || 0) > 0)
        : savedDrafts.value;
    if (!searchQuery.value) return drafts;
    const lowerQuery = searchQuery.value.toLowerCase();

    return drafts.filter((draft) =>
        (draft.project_name || 'Untitled Application')
            .toLowerCase()
            .includes(lowerQuery),
    );
});

const filteredProjects = computed(() => {
    const projects = messagesOnly.value
        ? submittedProjects.value.filter(
              (project) => (project.unread_messages || 0) > 0,
          )
        : submittedProjects.value;
    if (!searchQuery.value) return projects;
    const lowerQuery = searchQuery.value.toLowerCase();

    return projects.filter((project) =>
        [
            project.project_name || 'Untitled Application',
            project.application_number,
            project.permit_number,
            project.submission_type,
            project.industrial_sector,
        ]
            .join(' ')
            .toLowerCase()
            .includes(lowerQuery),
    );
});

const cardDate = (iso: string) =>
    iso ? new Date(iso).toLocaleDateString() : '';

const labelled = (label: string, value: string) =>
    value ? `${label}: ${value}` : '';

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
                v-model:messages-only="messagesOnly"
                :tabs="dashboardTabs"
                :last-updated="lastUpdated"
                :sort-options="sortOptions"
                messages-only-label="Only projects with unread messages"
                @refresh="loadDashboardData"
            />

            <div
                v-if="isLoading"
                class="loading-state"
            >
                <ProgressSpinner
                    style="width: 50px; height: 50px"
                    stroke-width="4"
                />
                <p>Loading submissions...</p>
            </div>

            <div
                v-else
                class="tab-content-container"
            >
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
                                :cap-date="cardDate(project.created_date)"
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
                                    project.submission_type
                                        ? `Type: ${project.submission_type}`
                                        : ''
                                "
                                :body2="
                                    labelled('Permit', project.permit_number)
                                "
                                :body3="
                                    buildModuleSummary(project.module_progress)
                                "
                                :footer-date="cardDate(project.created_date)"
                                :footer-name="project.created_by_name"
                                :urgency="project.urgency || 0"
                                :unread-messages="project.unread_messages || 0"
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
                            <div
                                v-for="draft in filteredDrafts"
                                :key="draft.id"
                                class="draft-card-wrapper"
                            >
                                <Card
                                    :label="
                                        draft.project_name ||
                                        'Untitled Application'
                                    "
                                    :description="
                                        draft.submission_type || DRAFT_LABEL
                                    "
                                    :subtitle="`Last updated: ${cardDate(
                                        draft.updated_date ||
                                            draft.created_date,
                                    )}`"
                                    icon="fa fa-file-pen"
                                    class="dashboard-card ipa"
                                    :route="{
                                        name: routeNames.baseModule,
                                        query: { draftId: draft.id },
                                    }"
                                />
                                <Button
                                    type="button"
                                    class="draft-delete-btn"
                                    icon="fa fa-trash"
                                    :aria-label="$gettext('Delete draft')"
                                    @click="confirmDelete(draft)"
                                />
                            </div>
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

    <Dialog
        v-model:visible="deleteState.visible"
        modal
        :closable="false"
        :header="$gettext('Delete draft?')"
        :style="{ width: '28rem' }"
    >
        <p>
            {{
                $gettext(
                    'This permanently deletes the draft. This action cannot be undone.',
                )
            }}
        </p>
        <template #footer>
            <Button
                :label="$gettext('Cancel')"
                text
                :disabled="deleteState.busy"
                @click="deleteState.visible = false"
            />
            <Button
                :label="$gettext('Delete')"
                severity="danger"
                :loading="deleteState.busy"
                @click="performDelete"
            />
        </template>
    </Dialog>

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

.loading-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 3rem;
    color: #555;
}

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

/* ProjectCard clamps its title to two lines with overflow:hidden at
   line-height 1.1, which is shorter than the glyphs and cuts the descenders
   off "g", "y" and friends. */
.dashboard-div-flex :deep(.bodyTitle) {
    line-height: 1.35;
}

/* CenterCard ships from bcgov_arches_common, so its body text is sized here.
   px, not rem: the root is 62%, so rem values land on fractional pixels. */
.dashboard-card :deep(.description) {
    font-size: 18px;
}

.dashboard-card :deep(.subtitle) {
    font-size: 14px;
}

.draft-card-wrapper {
    position: relative;
    display: inline-block;
    transition: transform 0.2s ease;
}

/* Lift the wrapper so the card and its delete button rise together on hover,
   mirroring the card's own hover (lift + shadow). Cancel the card's inner lift
   so the movement isn't doubled, and drive its shadow from the wrapper so the
   effect is identical whether the pointer is over the card or the trash icon. */
.draft-card-wrapper:hover {
    transform: translateY(-2px);
}

.draft-card-wrapper:hover :deep(.bcgov-custom-card) {
    transform: none;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.draft-delete-btn {
    position: absolute;
    bottom: 2.5rem;
    right: 2.5rem;
    z-index: 1;
    border: none;
    background: transparent;
    padding: 0.4rem;
    cursor: pointer;
    color: #6c757d;
    font-size: 1.1rem;
    line-height: 1;
    transition: color 0.2s ease;
}

.draft-delete-btn:hover {
    color: #c0392b;
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

:deep(.bodyTitle) {
    line-height: 1.3 !important;
}
</style>
