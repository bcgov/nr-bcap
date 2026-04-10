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
    <FieldSet legend="Methods">
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="null"
            graph-slug="Methods"
            node-alias=""
            @update:value="updateValue($event, 'Methods')"
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="null"
            graph-slug="pre-field research"
            node-alias=""
            @update:value="updateValue($event, '')"
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="null"
            graph-slug="archaeological potential"
            node-alias=""
            @update:value="updateValue($event, '')"
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="null"
            graph-slug="subsurface testing"
            node-alias=""
            @update:value="updateValue($event, '')"
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="null"
            graph-slug="transport and lab methods"
            node-alias=""
            @update:value="updateValue($event, '')"
        />
    </FieldSet>
</template>

<style></style>
