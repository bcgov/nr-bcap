<script setup lang="ts">
import GenericWidget from '@/arches_component_lab/generics/GenericWidget/GenericWidget.vue';
import { EDIT } from '@/arches_component_lab/widgets/constants.ts';
import FieldSet from 'primevue/fieldset';
import type {
    AliasedNodeData,
    CardXNodeXWidgetData,
} from '@/arches_component_lab/types.ts';
const isValid = () => {
    return true;
};

const updateValue = (newValue: AliasedNodeData, attribute_name: string) => {
    console.log(newValue, attribute_name);
};

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
    <FieldSet legend="Initial Information">
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="null"
            graph-slug="permit_application"
            node-alias="project_description"
            @update:value="updateValue($event, 'project_description')"
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="null"
            graph-slug="permit_application"
            node-alias="assessment_approach"
            @update:value="updateValue($event, 'assessment_approach')"
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="null"
            graph-slug="permit_application"
            node-alias="fn_file_numbers"
            @update:value="updateValue($event, 'fn_file_numbers')"
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="null"
            :card-x-node-x-widget-data-overrides="mapOverrides"
            graph-slug="permit_application"
            node-alias="project_boundary"
            @update:value="updateValue($event, 'project_boundary')"
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="null"
            graph-slug="permit_application"
            node-alias="scope_of_work"
            @update:value="updateValue($event, 'scope_of_work')"
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="null"
            graph-slug="permit_application"
            node-alias="are_ancestral_remains_anticipated"
            @update:value="
                updateValue($event, 'are_ancestral_remains_anticipated')
            "
        />
    </FieldSet>
    <br />
</template>

<style></style>
