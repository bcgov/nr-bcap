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
        'permit_scope',
        emit,
    );

const objectivesDoNotAlign = computed(
    () =>
        typedDraftData.value?.permit_scope?.aliased_data?.permit_scope_hip
            ?.aliased_data?.hip_confirms_objectives_align?.node_value === false,
);

defineExpose({ isValid });
</script>

<template>
    <Form
        :validate-on-blur="true"
        :validate-on-value-update="true"
        :validate-on-mount="false"
    >
        <FieldSet legend="Permit Objectives">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.permit_scope?.aliased_data?.permit_scope_hip
                        ?.aliased_data?.hip_confirms_objectives_align
                "
                graph-slug="hca_permit_application"
                node-alias="hip_confirms_objectives_align"
                @update:aliased-node-data="
                    updateValue($event, 'hip_confirms_objectives_align', [
                        'permit_scope',
                        'permit_scope_hip',
                    ])
                "
            />
            <GenericWidget
                v-if="objectivesDoNotAlign"
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.permit_scope?.aliased_data?.permit_scope_hip
                        ?.aliased_data?.hip_objectives_non_alignment
                "
                graph-slug="hca_permit_application"
                node-alias="hip_objectives_non_alignment"
                @update:aliased-node-data="
                    updateValue($event, 'hip_objectives_non_alignment', [
                        'permit_scope',
                        'permit_scope_hip',
                    ])
                "
            />
        </FieldSet>

        <FieldSet legend="Additional Objectives">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.permit_scope?.aliased_data?.permit_scope_hip
                        ?.aliased_data?.hip_other_objectives
                "
                graph-slug="hca_permit_application"
                node-alias="hip_other_objectives"
                @update:aliased-node-data="
                    updateValue($event, 'hip_other_objectives', [
                        'permit_scope',
                        'permit_scope_hip',
                    ])
                "
            />
        </FieldSet>
    </Form>
</template>
