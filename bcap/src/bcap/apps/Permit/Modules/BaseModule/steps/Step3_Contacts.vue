<script setup lang="ts">
import { computed } from 'vue';
import GenericWidget from '@/arches_component_lab/generics/GenericWidget/GenericWidget.vue';
import { EDIT } from '@/arches_component_lab/widgets/constants.ts';
import FieldSet from 'primevue/fieldset';
import { useDraftStep } from '@/bcap/composables/useDraftStep.ts';

const { draftData, isValid, updateValue } = useDraftStep();

// 1. Define the exact shapes Arches might return for this field
type ArchesNode =
    | {
          display_value?: string;
          value?: boolean | string;
      }
    | boolean
    | null
    | undefined;

const hasRetainedArchaeologist = computed(() => {
    const node = draftData?.value?.application_contacts?.aliased_data
        ?.has_retained_archaeologist as ArchesNode;

    if (node === null || node === undefined) return null;

    if (typeof node === 'boolean') {
        return node ? 'yes' : 'no';
    }

    if (
        typeof node === 'object' &&
        'display_value' in node &&
        typeof node.display_value === 'string'
    ) {
        return node.display_value.toLowerCase();
    }

    if (typeof node === 'object' && 'value' in node) {
        if (node.value === true) return 'yes';
        if (node.value === false) return 'no';
    }

    return null;
});

defineExpose({ isValid });
</script>

<template>
    <FieldSet>
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="
                draftData?.application_contacts?.aliased_data
                    ?.application_proponent
            "
            graph-slug="permit_application"
            node-alias="application_proponent"
            @update:value="
                updateValue(
                    $event,
                    'application_proponent',
                    'application_contacts',
                )
            "
        />

        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="
                draftData?.application_contacts?.aliased_data
                    ?.has_retained_archaeologist
            "
            graph-slug="permit_application"
            node-alias="has_retained_archaeologist"
            @update:value="
                updateValue(
                    $event,
                    'has_retained_archaeologist',
                    'application_contacts',
                )
            "
        />

        <GenericWidget
            v-if="hasRetainedArchaeologist === 'no'"
            class="description-box"
            :mode="EDIT"
            :aliased-node-data="
                draftData?.application_contacts?.aliased_data
                    ?.rationale_for_no_archaeologist
            "
            graph-slug="permit_application"
            node-alias="rationale_for_no_archaeologist"
            @update:value="
                updateValue(
                    $event,
                    'rationale_for_no_archaeologist',
                    'application_contacts',
                )
            "
        />

        <GenericWidget
            v-if="hasRetainedArchaeologist === 'yes'"
            :mode="EDIT"
            :aliased-node-data="
                draftData?.application_contacts?.aliased_data
                    ?.application_archaeologist
            "
            graph-slug="permit_application"
            node-alias="application_archaeologist"
            @update:value="
                updateValue(
                    $event,
                    'application_archaeologist',
                    'application_contacts',
                )
            "
        />
    </FieldSet>
    <br />
</template>

<style scoped>
.description-box {
    margin-top: 1rem;
}
</style>
