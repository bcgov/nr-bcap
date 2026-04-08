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
        label: $gettext('Submit Permit Application'),
        description: $gettext('New HCA Permit Application'),
        subtitle: $gettext('Start a new HCA Permit Application process'),
        icon: 'fa fa-square-plus',
        class: 'dashboard-card ipa',
        routeName: routeNames.newPermit,
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
                    :key="item.routeName"
                    :label="$gettext(item.label)"
                    :description="$gettext(item.description)"
                    :subtitle="$gettext(item.subtitle)"
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
</style>
