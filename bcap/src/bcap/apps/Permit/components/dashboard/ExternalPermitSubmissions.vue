<script setup lang="ts">
import { ref } from 'vue';
import Panel from 'primevue/panel';
import Fluid from 'primevue/fluid';
import { useGettext } from 'vue3-gettext';
import Card from '@/bcgov_arches_common/components/card/CenterCard.vue';

import { routeNames } from '@/bcap/apps/Permit/routes.ts';

const { $gettext } = useGettext();
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
</script>

<template>
    <Panel
        header="Workflows"
        class="full-height"
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
</template>

<style scoped>
.dashboard-div-flex {
    display: flex;
    flex-wrap: wrap;
}

.dashboard-card {
    width: 225px !important;
    aspect-ratio: 1 / 1;
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
