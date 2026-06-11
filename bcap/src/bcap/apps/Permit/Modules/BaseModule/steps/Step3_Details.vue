<script setup lang="ts">
import { inject, type Ref } from 'vue';
import GenericWidget from '@/arches_component_lab/generics/GenericWidget/GenericWidget.vue';
import { EDIT } from '@/arches_component_lab/widgets/constants.ts';
import FieldSet from 'primevue/fieldset';
import type {
    AliasedNodeData,
    CardXNodeXWidgetData,
} from '@/arches_component_lab/types.ts';
import { saveFieldToBackend } from '@/bcap/util.ts';

const draftId = inject<Ref<string | null>>('draftId');
const draftData = inject<Ref<Record<string, unknown>>>('draftData');
const graphSlug = 'permit_application';

const isValid = () => {
    return true;
};

let timeoutId: ReturnType<typeof setTimeout>;

const updateValue = (newValue: AliasedNodeData, attribute_name: string) => {
    // update local state so the Review page sees it
    if (draftData?.value) {
        draftData.value[attribute_name] = newValue;
    }

    clearTimeout(timeoutId);

    // update the backend
    timeoutId = setTimeout(() => {
        if (draftId?.value) {
            saveFieldToBackend(
                draftId.value,
                graphSlug,
                attribute_name,
                newValue,
            );
        }
    }, 1000);
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
    <FieldSet legend="">
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="draftData?.assessment_approach"
            graph-slug="permit_application"
            node-alias="assessment_approach"
            @update:value="updateValue($event, 'assessment_approach')"
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="draftData?.fn_file_numbers"
            graph-slug="permit_application"
            node-alias="fn_file_numbers"
            @update:value="updateValue($event, 'fn_file_numbers')"
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="draftData?.project_boundary"
            :card-x-node-x-widget-data-overrides="mapOverrides"
            graph-slug="permit_application"
            node-alias="project_boundary"
            @update:value="updateValue($event, 'project_boundary')"
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="draftData?.industrial_sector"
            graph-slug="permit_application"
            node-alias="industrial_sector"
            @update:value="updateValue($event, 'industrial_sector')"
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="draftData?.alteration_details"
            graph-slug="permit_application"
            node-alias="alteration_details"
            @update:value="updateValue($event, 'alteration_details')"
        />
    </FieldSet>
    <br />
</template>

<style></style>
