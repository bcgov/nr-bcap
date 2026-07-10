<script setup lang="ts">
import { Form } from '@primevue/forms';
import { zInvestigationSection2PersonnelAliasedData } from '@/bcap/client/zod.gen.ts';
import GenericWidget from '@/arches_component_lab/generics/GenericWidget/GenericWidget.vue';
import { EDIT } from '@/arches_component_lab/widgets/constants.ts';
import FieldSet from 'primevue/fieldset';
import { useDraftStep } from '@/bcap/composables/useDraftStep.ts';

const emit = defineEmits(['update:step-is-valid']);
const { draftData, resolver, isValid, updateValue } = useDraftStep(
    zInvestigationSection2PersonnelAliasedData,
    'section_2_personnel',
    emit,
);
defineExpose({ isValid });
</script>
<template>
    <Form
        :resolver="resolver"
        :validate-on-blur="true"
        :validate-on-value-update="true"
        :validate-on-mount="false"
    >
        <FieldSet>
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.section_2_personnel?.aliased_data
                        ?.permit_deliverables
                "
                graph-slug="investigation"
                node-alias="permit_deliverables"
                @update:value="
                    updateValue(
                        $event,
                        'permit_deliverables',
                        'section_2_personnel',
                    )
                "
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.section_2_personnel?.aliased_data
                        ?.is_hca_compliant
                "
                graph-slug="investigation"
                node-alias="is_hca_compliant"
                @update:value="
                    updateValue(
                        $event,
                        'is_hca_compliant',
                        'section_2_personnel',
                    )
                "
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.section_2_personnel?.aliased_data
                        ?.field_directors
                "
                graph-slug="investigation"
                node-alias="field_directors"
                @update:value="
                    updateValue(
                        $event,
                        'field_directors',
                        'section_2_personnel',
                    )
                "
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.section_2_personnel?.aliased_data
                        ?.overseeing_archaeologist
                "
                graph-slug="investigation"
                node-alias="overseeing_archaeologist"
                @update:value="
                    updateValue(
                        $event,
                        'overseeing_archaeologist',
                        'section_2_personnel',
                    )
                "
            />
        </FieldSet>
    </Form>
    <br />
</template>

<style></style>
