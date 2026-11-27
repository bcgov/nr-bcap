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

const hasRelatedAlterations = computed(
    () =>
        typedDraftData.value?.permit_scope?.aliased_data?.permit_scope_hip
            ?.aliased_data?.hip_has_related_alterations?.node_value,
);

defineExpose({ isValid });
</script>

<template>
    <Form
        :validate-on-blur="true"
        :validate-on-value-update="true"
        :validate-on-mount="false"
    >
        <FieldSet legend="Related Alterations">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.permit_scope?.aliased_data?.permit_scope_hip
                        ?.aliased_data?.hip_has_related_alterations
                "
                graph-slug="hca_permit_application"
                node-alias="hip_has_related_alterations"
                @update:aliased-node-data="
                    updateValue($event, 'hip_has_related_alterations', [
                        'permit_scope',
                        'permit_scope_hip',
                    ])
                "
            />
            <GenericWidget
                v-if="hasRelatedAlterations === true"
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.permit_scope?.aliased_data?.permit_scope_hip
                        ?.aliased_data?.hip_alteration_type
                "
                graph-slug="hca_permit_application"
                node-alias="hip_alteration_type"
                @update:aliased-node-data="
                    updateValue($event, 'hip_alteration_type', [
                        'permit_scope',
                        'permit_scope_hip',
                    ])
                "
            />
        </FieldSet>

        <FieldSet legend="First Nation File Numbers">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.permit_scope?.aliased_data?.permit_scope_hip
                        ?.aliased_data?.hip_first_nation_file_numbers
                "
                graph-slug="hca_permit_application"
                node-alias="hip_first_nation_file_numbers"
                @update:aliased-node-data="
                    updateValue($event, 'hip_first_nation_file_numbers', [
                        'permit_scope',
                        'permit_scope_hip',
                    ])
                "
            />
        </FieldSet>

        <FieldSet legend="Additional Discussion">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.permit_scope?.aliased_data?.permit_scope_hip
                        ?.aliased_data?.hip_additional_discussion
                "
                graph-slug="hca_permit_application"
                node-alias="hip_additional_discussion"
                @update:aliased-node-data="
                    updateValue($event, 'hip_additional_discussion', [
                        'permit_scope',
                        'permit_scope_hip',
                    ])
                "
            />
        </FieldSet>
    </Form>
</template>
