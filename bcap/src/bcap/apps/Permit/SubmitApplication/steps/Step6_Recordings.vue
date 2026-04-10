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
            graph-slug="if the excavation approach is compliant with standard guidance"
            node-alias=""
            @update:value="updateValue($event, '')"
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="null"
            graph-slug="other approaches"
            node-alias=""
            @update:value="updateValue($event, 'other approaches')"
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="null"
            graph-slug="will rock art recording will be compliant with standard guidance"
            node-alias=""
            @update:value="updateValue($event, '')"
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="null"
            graph-slug="alternate way to record rock art"
            node-alias=""
            @update:value="updateValue($event, '')"
        />
    </FieldSet>
</template>

<style></style>
