<script setup lang="ts">
import { computed } from 'vue';
import { Form } from '@primevue/forms';
import GenericWidget from '@/arches_vue_components/generics/GenericWidget/GenericWidget.vue';
import { EDIT } from '@/arches_vue_components/widgets/constants.ts';
import FieldSet from 'primevue/fieldset';
import { useDraftStep } from '@/bcap/composables/useDraftStep.ts';
import type { HcaPermitApplicationResourceAliasedData } from '@/bcap/client/types.gen.ts';

const emit = defineEmits(['update:step-is-valid']);

const { draftData, typedDraftData, isValid, updateValue } =
    useDraftStep<HcaPermitApplicationResourceAliasedData>(
        undefined,
        'methodology',
        emit,
    );

const machineAssistedFieldsVisible = computed(
    () =>
        typedDraftData.value?.methodology?.aliased_data
            ?.has_machine_assisted_methods?.node_value === true,
);

defineExpose({ isValid });
</script>

<template>
    <Form
        :validate-on-blur="true"
        :validate-on-value-update="true"
        :validate-on-mount="false"
    >
        <FieldSet legend="Machine-Assisted Methods">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.methodology?.aliased_data
                        ?.has_machine_assisted_methods
                "
                graph-slug="hca_permit_application"
                node-alias="has_machine_assisted_methods"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'has_machine_assisted_methods',
                        'methodology',
                    )
                "
            />
            <GenericWidget
                v-if="machineAssistedFieldsVisible"
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.methodology?.aliased_data
                        ?.machine_assisted_methods_description
                "
                graph-slug="hca_permit_application"
                node-alias="machine_assisted_methods_description"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'machine_assisted_methods_description',
                        'methodology',
                    )
                "
            />
            <GenericWidget
                v-if="machineAssistedFieldsVisible"
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.methodology?.aliased_data
                        ?.machine_assisted_approach
                "
                graph-slug="hca_permit_application"
                node-alias="machine_assisted_approach"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'machine_assisted_approach',
                        'methodology',
                    )
                "
            />
        </FieldSet>
    </Form>
</template>
