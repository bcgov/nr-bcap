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
    <FieldSet legend="Ancestral Remains">
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="null"
            graph-slug="permit_application"
            node-alias="ancestral_remains_approach_compliant"
            @update:value="
                updateValue($event, 'ancestral_remains_approach_compliant')
            "
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="null"
            graph-slug="permit_application"
            node-alias="alternate_ancestral_remains_approach"
            @update:value="
                updateValue($event, 'alternate_ancestral_remains_approach')
            "
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="null"
            graph-slug="permit_application"
            node-alias="ancestral_remains_approach_methods"
            @update:value="
                updateValue($event, 'ancestral_remains_approach_methods')
            "
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="null"
            graph-slug="permit_application"
            node-alias="ancestral_remains_approach_additional_comments"
            @update:value="
                updateValue(
                    $event,
                    'ancestral_remains_approach_additional_comments',
                )
            "
        />
    </FieldSet>
</template>

<style></style>
