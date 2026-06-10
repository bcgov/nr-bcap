<script setup lang="ts">
import GenericWidget from '@/arches_component_lab/generics/GenericWidget/GenericWidget.vue';
import { EDIT } from '@/arches_component_lab/widgets/constants.ts';
import FieldSet from 'primevue/fieldset';
import type { AliasedNodeData } from '@/arches_component_lab/types.ts';
const isValid = () => {
    return true;
};

const updateValue = (newValue: AliasedNodeData, attribute_name: string) => {
    console.log(newValue, attribute_name);
};

defineExpose({ isValid });
</script>
<template>
    <FieldSet legend="">
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="null"
            graph-slug="permit_application"
            node-alias="project_name"
            @update:value="updateValue($event, 'project_name')"
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="null"
            graph-slug="permit_application"
            node-alias="application_id"
            @update:value="updateValue($event, 'application_id')"
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="null"
            graph-slug="permit_application"
            node-alias="project_type"
            @update:value="updateValue($event, 'project_type')"
        />
        <GenericWidget
            class="description-box"
            :mode="EDIT"
            :aliased-node-data="null"
            graph-slug="permit_application"
            node-alias="project_description"
            @update:value="updateValue($event, 'project_description')"
        />
    </FieldSet>
    <br />
</template>

<style>
GenericWidget {
    max-width: 75%;
}
</style>
