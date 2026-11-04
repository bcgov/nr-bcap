<script setup lang="ts">
import { Form } from '@primevue/forms';
import { zInvestigationSection2PersonnelAliasedData } from '@/bcap/client/zod.gen.ts';
import GenericWidget from '@/arches_vue_components/generics/GenericWidget/GenericWidget.vue';
import { EDIT } from '@/arches_vue_components/widgets/constants.ts';
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
                @update:aliased-node-data="
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
                @update:aliased-node-data="
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
                @update:aliased-node-data="
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
                @update:aliased-node-data="
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
