<script setup lang="ts">
import { computed } from 'vue';
import GenericWidget from '@/arches_vue_components/generics/GenericWidget/GenericWidget.vue';
import { EDIT } from '@/arches_vue_components/widgets/constants.ts';
import FieldSet from 'primevue/fieldset';
import { useDraftStep } from '@/bcap/composables/useDraftStep.ts';

const { draftData, isValid, updateValue } = useDraftStep();

// The shapes Arches might return for this field.
type ArchesNode =
    | {
          display_value?: string;
          value?: boolean | string;
      }
    | boolean
    | null
    | undefined;

const hasRetainedArchaeologist = computed(() => {
    const node = draftData?.value?.service_request_contacts?.aliased_data
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
                draftData?.service_request_contacts?.aliased_data
                    ?.application_proponent
            "
            graph-slug="bcap_service_request"
            node-alias="application_proponent"
            @update:aliased-node-data="
                updateValue(
                    $event,
                    'application_proponent',
                    'service_request_contacts',
                )
            "
        />

        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="
                draftData?.service_request_contacts?.aliased_data
                    ?.has_retained_archaeologist
            "
            graph-slug="bcap_service_request"
            node-alias="has_retained_archaeologist"
            @update:aliased-node-data="
                updateValue(
                    $event,
                    'has_retained_archaeologist',
                    'service_request_contacts',
                )
            "
        />

        <GenericWidget
            v-if="hasRetainedArchaeologist === 'no'"
            class="description-box"
            :mode="EDIT"
            :aliased-node-data="
                draftData?.service_request_contacts?.aliased_data
                    ?.rationale_for_no_archaeologist
            "
            graph-slug="bcap_service_request"
            node-alias="rationale_for_no_archaeologist"
            @update:aliased-node-data="
                updateValue(
                    $event,
                    'rationale_for_no_archaeologist',
                    'service_request_contacts',
                )
            "
        />

        <GenericWidget
            v-if="hasRetainedArchaeologist === 'yes'"
            :mode="EDIT"
            :aliased-node-data="
                draftData?.service_request_contacts?.aliased_data
                    ?.application_archaeologist
            "
            graph-slug="bcap_service_request"
            node-alias="application_archaeologist"
            @update:aliased-node-data="
                updateValue(
                    $event,
                    'application_archaeologist',
                    'service_request_contacts',
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
