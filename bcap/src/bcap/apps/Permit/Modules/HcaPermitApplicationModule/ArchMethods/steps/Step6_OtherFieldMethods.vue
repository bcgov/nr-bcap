<script setup lang="ts">
import { Form } from '@primevue/forms';
import GenericWidget from '@/arches_vue_components/generics/GenericWidget/GenericWidget.vue';
import { EDIT } from '@/arches_vue_components/widgets/constants.ts';
import FieldSet from 'primevue/fieldset';
import { useDraftStep } from '@/bcap/composables/useDraftStep.ts';
import type { HcaPermitApplicationResourceAliasedData } from '@/bcap/client/types.gen.ts';

const emit = defineEmits(['update:step-is-valid']);

const { draftData, isValid, updateValue } =
    useDraftStep<HcaPermitApplicationResourceAliasedData>(
        undefined,
        'methodology',
        emit,
    );

defineExpose({ isValid });
</script>

<template>
    <Form
        :validate-on-blur="true"
        :validate-on-value-update="true"
        :validate-on-mount="false"
    >
        <FieldSet legend="Other Field Methods">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.methodology?.aliased_data?.other_field_methods
                "
                graph-slug="hca_permit_application"
                node-alias="other_field_methods"
                @update:aliased-node-data="
                    updateValue($event, 'other_field_methods', 'methodology')
                "
            />
        </FieldSet>
    </Form>
</template>
