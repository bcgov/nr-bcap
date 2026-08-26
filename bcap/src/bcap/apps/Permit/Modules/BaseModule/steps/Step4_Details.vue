<script setup lang="ts">
import GenericWidget from '@/arches_vue_components/generics/GenericWidget/GenericWidget.vue';
import { EDIT } from '@/arches_vue_components/widgets/constants.ts';
import FieldSet from 'primevue/fieldset';
import type { CardXNodeXWidgetData } from '@/arches_vue_components/types.ts';
import { useDraftStep } from '@/bcap/composables/useDraftStep.ts';

const { draftData, isValid, updateValue } = useDraftStep();

const mapOverrides = {
    widget: {
        widgetid: '',
        component:
            'bcgov_arches_common/widgets/MapDropZoneWidget/MapDropZoneWidget.vue',
    },
} satisfies Partial<CardXNodeXWidgetData>;

defineExpose({ isValid });
</script>

<template>
    <FieldSet legend="">
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="
                draftData?.proposed_project?.aliased_data
                    ?.development_project_details?.aliased_data
                    ?.industrial_sector
            "
            graph-slug="permit_application"
            node-alias="industrial_sector"
            @update:aliased-node-data="
                updateValue($event, 'industrial_sector', [
                    'proposed_project',
                    'development_project_details',
                ])
            "
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="
                draftData?.proposed_project?.aliased_data?.project_boundary
            "
            :card-x-node-x-widget-data-overrides="mapOverrides"
            graph-slug="permit_application"
            node-alias="project_boundary"
            @update:aliased-node-data="
                updateValue($event, 'project_boundary', 'proposed_project')
            "
        />
    </FieldSet>
    <br />
</template>

<style></style>
