<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import Panel from 'primevue/panel';
import Fluid from 'primevue/fluid';
import { useGettext } from 'vue3-gettext';
import Card from '@/bcgov_arches_common/components/card/CenterCard.vue';
import SortingBar from './SortingBar.vue';

import { routeNames } from '@/bcap/apps/Permit/routes.ts';

const { $gettext } = useGettext();
const savedDrafts = ref<ResourceDraft[]>([]);

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
    {
        id: 'alterations-module',
        label: $gettext('Add Alterations Module'),
        description: $gettext('New Alterations Application'),
        subtitle: $gettext('Start a new Alterations Application'),
        icon: 'fa fa-edit',
        class: 'dashboard-card ipa',
        routeName: routeNames.alterationsModule,
    },
    {
        id: 'collection-module',
        label: $gettext('Add Collection Module'),
        description: $gettext('New Collection Application'),
        subtitle: $gettext('Start a new Collection Application'),
        icon: 'fa fa-boxes-stacked',
        class: 'dashboard-card ipa',
        routeName: routeNames.collectionModule,
    },
    {
        id: 'inspection-module',
        label: $gettext('Add Inspection Module'),
        description: $gettext('New Inspection Application'),
        subtitle: $gettext('Start a new Inspection Application'),
        icon: 'fa fa-clipboard-check',
        class: 'dashboard-card ipa',
        routeName: routeNames.inspectionModule,
    },
    {
        id: 'investigation-module',
        label: $gettext('Add Investigation Module'),
        description: $gettext('New Investigation Application'),
        subtitle: $gettext('Start a new Investigation Application'),
        icon: 'fa fa-magnifying-glass',
        class: 'dashboard-card ipa',
        routeName: routeNames.investigationModule,
    },
    {
        id: 'methods-module',
        label: $gettext('Add Methods Module'),
        description: $gettext('New Methods Application'),
        subtitle: $gettext('Start a new Methods Application'),
        icon: 'fa fa-flask',
        class: 'dashboard-card ipa',
        routeName: routeNames.methodsModule,
    },
    {
        id: 'recordings-module',
        label: $gettext('Add Recordings Module'),
        description: $gettext('New Recordings Application'),
        subtitle: $gettext('Start a new Recordings Application'),
        icon: 'fa fa-camera',
        class: 'dashboard-card ipa',
        routeName: routeNames.recordingsModule,
    },
]);

const fetchDrafts = async () => {
    try {
        const response = await fetch(
            '/bcap/api/resource_draft/permit_application',
        );
        if (response.ok) {
            savedDrafts.value = await response.json();
            lastUpdated.value = new Date();
        }
    } catch (error) {
        console.error('Failed to load drafts for dashboard:', error);
    }
};

onMounted(() => {
    fetchDrafts();
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
                v-model:activeTab="activeTab"
                v-model:search="searchQuery"
                v-model:currentSort="currentSort"
                v-model:sortOrder="sortOrder"
                :tabs="dashboardTabs"
                :last-updated="lastUpdated"
                :sort-options="sortOptions"
                @refresh="fetchDrafts"
            />

            <div class="tab-content-container">
                <div v-if="activeTab === 'my_projects'">
                    <p class="text-muted">No submitted projects found.</p>
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
