<script setup lang="ts">
import { ref, reactive, onMounted, computed, watch } from 'vue';
import { useRouter } from 'vue-router';
import Panel from 'primevue/panel';
import Fluid from 'primevue/fluid';
import Dialog from 'primevue/dialog';
import Button from 'primevue/button';
import ProgressSpinner from 'primevue/progressspinner';
import { useGettext } from 'vue3-gettext';
import SortingBar from './SortingBar.vue';
import {
    fetchCompanyProjects,
    fetchDraftCards,
    fetchMyProjects,
    deleteDraft,
} from '@/bcap/apps/Permit/api.ts';
import { buildModuleSummary } from '@/bcap/apps/Permit/moduleSummary.ts';
import { GraphSlug } from '@/bcap/apps/Permit/graphSlug.ts';
import { permitModules } from './permitModules.ts';
import type { ExternalDashboardCard } from '@/bcap/client/types.gen.ts';
import ProjectCard from '@/bcgov_arches_common/components/card/ProjectCard.vue';
import { routeNames } from '@/bcap/apps/Permit/routes.ts';
import { useConfirmAction } from '@/bcap/apps/Permit/composables/useConfirmAction.ts';

const { $gettext } = useGettext();
const router = useRouter();
const cards = reactive({
    savedDrafts: [] as ExternalDashboardCard[],
    submittedProjects: [] as ExternalDashboardCard[],
    companyProjects: [] as ExternalDashboardCard[],
});

enum DashboardTab {
    MyProjects = 'my_projects',
    CompanyProjects = 'company_projects',
    Drafts = 'drafts',
}

const EXTERNAL_TAB_KEY = 'bcap.externalDashboard.tab';
const EXTERNAL_TABS: string[] = Object.values(DashboardTab);
const storedTab = localStorage.getItem(EXTERNAL_TAB_KEY) ?? '';
const ui = reactive({
    activeTab: EXTERNAL_TABS.includes(storedTab)
        ? (storedTab as DashboardTab)
        : DashboardTab.Drafts,
    searchQuery: '',
    currentSort: 'default',
    messagesOnly: false,
    sortOrder: 'desc' as 'asc' | 'desc',
    lastUpdated: new Date(),
});
watch(
    () => ui.activeTab,
    (tab) => localStorage.setItem(EXTERNAL_TAB_KEY, tab),
);

const sortOptions = [
    { label: 'Name', value: 'name' },
    { label: 'Date Updated', value: 'updated' },
    { label: 'Date Created', value: 'created' },
];

const dashboardTabs = [
    { label: 'My Projects', value: DashboardTab.MyProjects },
    { label: 'Company Projects', value: DashboardTab.CompanyProjects },
    { label: 'Drafts', value: DashboardTab.Drafts },
];

const isLoading = ref(true);

const loadDashboardData = async () => {
    isLoading.value = true;
    try {
        const [draftsData, projectsData, companyData] = await Promise.all([
            fetchDraftCards(),
            fetchMyProjects(),
            fetchCompanyProjects(),
        ]);

        cards.savedDrafts = draftsData;
        cards.submittedProjects = projectsData;
        cards.companyProjects = companyData;
        ui.lastUpdated = new Date();
    } catch (error) {
        console.error('Failed to load dashboard data:', error);
    } finally {
        isLoading.value = false;
    }
};

onMounted(() => {
    loadDashboardData();
});

const draftModule = (draft: ExternalDashboardCard) =>
    permitModules.find((mod) => mod.id === draft.graph_slug);

// The module list calls the application itself "Filing Summary", which reads
// wrong on a draft card.
const DRAFT_LABELS: Record<string, string> = {
    [GraphSlug.PermitApplication]: 'Permit Application',
};

const draftLabel = (draft: ExternalDashboardCard) =>
    DRAFT_LABELS[draft.graph_slug ?? ''] ||
    draftModule(draft)?.menuLabel ||
    'Permit Application';

// A module draft borrows its permit's name and filing type, so it has to say
// which module it is; an application draft is the application.
const isModuleDraft = (draft: ExternalDashboardCard) =>
    !!draft.graph_slug && draft.graph_slug !== GraphSlug.PermitApplication;

// A module draft names the module alone; the permit it hangs off is already on
// the card as the application number.
const draftTitle = (draft: ExternalDashboardCard) =>
    isModuleDraft(draft)
        ? draftLabel(draft)
        : draft.project_name || `Untitled ${draftLabel(draft)}`;

const draftDescription = (draft: ExternalDashboardCard) =>
    isModuleDraft(draft)
        ? `${draftLabel(draft)} Draft`
        : draft.submission_type || 'Permit Application Draft';

// A draft under a permit opens that permit's filing summary; one with no permit
// yet has nothing to summarise, so it resumes its workflow instead.
const draftRoute = (draft: ExternalDashboardCard) =>
    draft.permit_application_id
        ? {
              name: routeNames.permitDetails,
              params: { id: draft.permit_application_id },
              query: { draft: draft.id },
          }
        : {
              name: draftModule(draft)?.routeName || routeNames.baseModule,
              query: { draftId: draft.id },
          };

const {
    state: deleteState,
    open: confirmDelete,
    confirm: performDelete,
} = useConfirmAction<ExternalDashboardCard>(async (draft) => {
    await deleteDraft(
        draft.graph_slug || GraphSlug.PermitApplication,
        draft.id,
    );
    cards.savedDrafts = cards.savedDrafts.filter((d) => d.id !== draft.id);
});

const filteredDrafts = computed(() => {
    const drafts = ui.messagesOnly
        ? cards.savedDrafts.filter((draft) => (draft.unread_messages || 0) > 0)
        : cards.savedDrafts;
    if (!ui.searchQuery) return drafts;
    const lowerQuery = ui.searchQuery.toLowerCase();

    return drafts.filter((draft) =>
        draftTitle(draft).toLowerCase().includes(lowerQuery),
    );
});

// The two project tabs share every card, filter and sort; only the source
// differs.
const tabProjects = computed(() =>
    ui.activeTab === DashboardTab.CompanyProjects
        ? cards.companyProjects
        : cards.submittedProjects,
);

const filteredProjects = computed(() => {
    const projects = ui.messagesOnly
        ? tabProjects.value.filter(
              (project) => (project.unread_messages || 0) > 0,
          )
        : tabProjects.value;
    if (!ui.searchQuery) return projects;
    const lowerQuery = ui.searchQuery.toLowerCase();

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

const shownCards = computed(() =>
    ui.activeTab === DashboardTab.Drafts
        ? filteredDrafts.value
        : filteredProjects.value,
);

const totalCards = computed(() =>
    ui.activeTab === DashboardTab.Drafts
        ? cards.savedDrafts
        : tabProjects.value,
);

const emptyProjectsNote = computed(() =>
    ui.activeTab === DashboardTab.CompanyProjects
        ? 'No company projects found.'
        : 'No submitted projects found.',
);

const cardDate = (iso?: string) =>
    iso ? new Date(iso).toLocaleDateString() : '';

const labelled = (label: string, value?: string) =>
    value ? `${label}: ${value}` : '';

const openResourceReport = (resourceId: string) => {
    router.push({
        name: routeNames.permitDetails,
        params: { id: resourceId },
    });
};
</script>

<template>
    <Panel class="full-height">
        <Fluid>
            <div class="start-banner">
                <div class="start-banner-text">
                    <p class="start-banner-title">
                        {{ $gettext('Start new workflow') }}
                    </p>
                    <p class="start-banner-subtitle">
                        {{
                            $gettext(
                                'Your progress saves as a draft as you go.',
                            )
                        }}
                    </p>
                </div>
                <router-link
                    class="start-banner-action"
                    :to="{ name: routeNames.baseModule }"
                >
                    <i class="fa-solid fa-plus"></i>
                    {{ $gettext('New HCA permit application') }}
                </router-link>
            </div>

            <SortingBar
                v-model:active-tab="ui.activeTab"
                v-model:search="ui.searchQuery"
                v-model:current-sort="ui.currentSort"
                v-model:sort-order="ui.sortOrder"
                v-model:messages-only="ui.messagesOnly"
                :tabs="dashboardTabs"
                :last-updated="ui.lastUpdated"
                :sort-options="sortOptions"
                messages-only-label="Unread messages only"
                :shown="isLoading ? 0 : shownCards.length"
                :total="isLoading ? 0 : totalCards.length"
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
                <div v-if="ui.activeTab !== DashboardTab.Drafts">
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
                                :search-query="ui.searchQuery"
                                @click="openResourceReport(project.id)"
                            />
                        </div>
                    </Fluid>
                    <p
                        v-else
                        class="text-muted"
                    >
                        {{ emptyProjectsNote }}
                    </p>
                </div>

                <div v-if="ui.activeTab === DashboardTab.Drafts">
                    <Fluid v-if="filteredDrafts.length > 0">
                        <div class="dashboard-div-flex">
                            <div
                                v-for="draft in filteredDrafts"
                                :key="draft.id"
                                class="draft-card-wrapper"
                            >
                                <ProjectCard
                                    :cap-priority="
                                        draft.priority_level === 'High'
                                    "
                                    :cap-label="draft.status || 'Draft'"
                                    :cap-date="
                                        cardDate(
                                            draft.updated_date ||
                                                draft.created_date,
                                        )
                                    "
                                    icon="fa-solid fa-file-pen"
                                    :body-title="draftTitle(draft)"
                                    :body-subtitle1="
                                        draft.application_number || 'No App #'
                                    "
                                    :body-subtitle2="draft.industrial_sector"
                                    :body1="
                                        labelled(
                                            'Type',
                                            draftDescription(draft),
                                        )
                                    "
                                    :body2="
                                        labelled(
                                            'Updated',
                                            cardDate(
                                                draft.updated_date ||
                                                    draft.created_date,
                                            ),
                                        )
                                    "
                                    :body3="
                                        buildModuleSummary(
                                            draft.module_progress,
                                        )
                                    "
                                    :urgency="draft.urgency || 0"
                                    :unread-messages="
                                        draft.unread_messages || 0
                                    "
                                    :footer-date="cardDate(draft.created_date)"
                                    :footer-name="draft.created_by_name"
                                    :search-query="ui.searchQuery"
                                    :route="draftRoute(draft)"
                                />
                                <Button
                                    type="button"
                                    class="draft-delete-btn"
                                    :label="$gettext('Remove')"
                                    :aria-label="$gettext('Delete draft')"
                                    :fluid="false"
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
.start-banner {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 1rem 1.5rem;
    margin: 1rem 0 2rem;
    padding: 1.25rem 1.75rem;
    box-sizing: border-box;
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-left: 6px solid var(--bc-navy, #003366);
    border-radius: 4px;
}

.start-banner-title {
    margin: 0;
    color: var(--bc-navy, #003366);
    font-size: 1.6rem;
    font-weight: 700;
}

.start-banner-subtitle {
    margin: 0.15rem 0 0;
    color: #6c757d;
    font-size: 1.4rem;
}

.start-banner-action {
    display: inline-flex;
    align-items: center;
    gap: 0.75rem;
    flex-shrink: 0;
    padding: 0.85rem 1.75rem;
    border-radius: 4px;
    background: var(--bc-navy, #003366);
    color: #ffffff;
    font-size: 1.45rem;
    font-weight: 700;
    text-decoration: none;
}

.start-banner-action:hover,
.start-banner-action:focus {
    background: #1d4b7d;
    color: #ffffff;
    text-decoration: none;
}

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
    gap: 1.5rem;
    margin: 0 -10px 1rem;
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

/* Bottom right, in the strip the card body reserves below its footer. */
.draft-delete-btn {
    position: absolute;
    bottom: 16px;
    right: 1.5rem;
    z-index: 1;
    width: auto;
    background: #ffffff;
    padding: 0.4rem 1.1rem;
    border: 1.5px solid #d1d5db;
    border-radius: 4px;
    cursor: pointer;
    color: var(--bc-navy, #003366);
    font-size: 14px;
    font-weight: 600;
    line-height: 1.3;
    transition:
        color 0.2s ease,
        border-color 0.2s ease;
}

.draft-delete-btn:hover {
    color: #c0392b;
    border-color: #c0392b;
}

.tab-content-container {
    min-height: 300px;
}

.text-muted {
    color: #6c757d;
    font-style: italic;
    padding: 1rem 0;
}

/* Taller than a project card, with the card's own footer pulled up, so the
   Remove button gets a strip of its own underneath. */
.draft-card-wrapper :deep(.project-card-link) {
    height: 310px;
}

.draft-card-wrapper :deep(.bcgov-card-body) {
    padding-bottom: 4rem;
}

/* A rule between the card's own footer and the Remove strip below it. */
.draft-card-wrapper :deep(.bcgov-card-footer) {
    padding-bottom: 0.75rem;
    border-bottom: 1px solid #e5e7eb;
}

/* Drafts only: lighter than the navy on a submitted project's card. */
.draft-card-wrapper :deep(.bcgov-card-cap) {
    background-color: #385a8a;
}

.draft-card-wrapper :deep(.body-icon-class) {
    color: #385a8a;
}

:deep(.bcgov-custom-card) {
    height: 100%;
}

:deep(.stack-icon) {
    font-size: 4.5rem !important;
    margin-bottom: 4rem !important;
}

:deep(.bcgov-card-header) {
    font-size: 1.25rem !important;
    font-weight: 600 !important;
    line-height: 1.2 !important;
}

:deep(.description) {
    font-size: 1.25rem !important;
    font-weight: bold !important;
    color: #3b3bff !important;
}

:deep(.subtitle) {
    color: #1a1a1a !important;
    font-size: 1.25rem !important;
}

:deep(.bodyTitle) {
    line-height: 1.3 !important;
}
</style>
