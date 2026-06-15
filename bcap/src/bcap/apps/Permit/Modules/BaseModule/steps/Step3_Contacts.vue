<script setup lang="ts">
import { inject, computed, type Ref } from 'vue';
import GenericWidget from '@/arches_component_lab/generics/GenericWidget/GenericWidget.vue';
import { EDIT } from '@/arches_component_lab/widgets/constants.ts';
import FieldSet from 'primevue/fieldset';
import type { AliasedNodeData } from '@/arches_component_lab/types.ts';
import { updateDraftValue } from '@/bcap/util.ts';
import type { ArchesDraftData } from '@/bcap/types.ts';

const draftId = inject<Ref<string | null>>('draftId');
const draftData = inject<Ref<ArchesDraftData>>('draftData');
const graphSlug = 'permit_application';

const isValid = () => {
    return true;
};

const updateValue = (
    newValue: AliasedNodeData,
    attribute_name: string,
    node_group_alias: string | string[],
) => {
    updateDraftValue(
        draftData?.value,
        draftId?.value,
        graphSlug,
        newValue,
        attribute_name,
        node_group_alias,
    );
};

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
    <FieldSet legend="Application Contacts">
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
