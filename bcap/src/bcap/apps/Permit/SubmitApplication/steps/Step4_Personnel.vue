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
    <FieldSet legend="Initial Information">
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="null"
            graph-slug="permit_application"
            node-alias="permit_deliverables"
            @update:value="updateValue($event, 'permit_deliverables')"
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="null"
            graph-slug="permit_application"
            node-alias="field_directors"
            @update:value="updateValue($event, 'field_directors')"
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="null"
            graph-slug="permit_application"
            node-alias="overseeing_archaeologist"
            @update:value="updateValue($event, 'overseeing_archaeologist')"
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="null"
            graph-slug="permit_application"
            node-alias="is_hca_compliant"
            @update:value="updateValue($event, 'is_hca_compliant')"
        />
    </FieldSet>
    <br />
</template>

<style></style>
