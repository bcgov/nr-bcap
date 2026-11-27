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
        'permit_scope',
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
        <FieldSet legend="Project Location">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.permit_scope?.aliased_data
                        ?.permit_scope_alteration?.aliased_data
                        ?.project_location
                "
                graph-slug="hca_permit_application"
                node-alias="project_location"
                @update:aliased-node-data="
                    updateValue($event, 'project_location', [
                        'permit_scope',
                        'permit_scope_alteration',
                    ])
                "
            />
        </FieldSet>

        <FieldSet legend="Project Description">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.permit_scope?.aliased_data
                        ?.permit_scope_alteration?.aliased_data
                        ?.alteration_project_description
                "
                graph-slug="hca_permit_application"
                node-alias="alteration_project_description"
                @update:aliased-node-data="
                    updateValue($event, 'alteration_project_description', [
                        'permit_scope',
                        'permit_scope_alteration',
                    ])
                "
            />
        </FieldSet>

        <FieldSet legend="Alteration Timing">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.permit_scope?.aliased_data
                        ?.permit_scope_alteration?.aliased_data
                        ?.alteration_timing
                "
                graph-slug="hca_permit_application"
                node-alias="alteration_timing"
                @update:aliased-node-data="
                    updateValue($event, 'alteration_timing', [
                        'permit_scope',
                        'permit_scope_alteration',
                    ])
                "
            />
        </FieldSet>
    </Form>
</template>
