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
    <FieldSet legend="Recordings">
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="null"
            graph-slug="permit_application"
            node-alias="is_excavation_approach_compliant"
            @update:value="
                updateValue($event, 'is_excavation_approach_compliant')
            "
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="null"
            graph-slug="permit_application"
            node-alias="alternate_excavation_approach"
            @update:value="updateValue($event, 'alternate_excavation_approach')"
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="null"
            graph-slug="permit_application"
            node-alias="is_rock_art_recording_compliant"
            @update:value="
                updateValue($event, 'is_rock_art_recording_compliant')
            "
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="null"
            graph-slug="permit_application"
            node-alias="alternate_rock_art_recording_approach"
            @update:value="
                updateValue($event, 'alternate_rock_art_recording_approach')
            "
        />
    </FieldSet>
    <br />
</template>

<style></style>
