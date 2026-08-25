<script setup lang="ts">
import { Form } from '@primevue/forms';
import { zDocumentSubmissionSubmissionAssessmentAliasedData } from '@/bcap/client/zod.gen.ts';
import GenericWidget from '@/arches_component_lab/generics/GenericWidget/GenericWidget.vue';
import { EDIT } from '@/arches_component_lab/widgets/constants.ts';
import FieldSet from 'primevue/fieldset';
import { useDraftStep } from '@/bcap/composables/useDraftStep.ts';

const emit = defineEmits(['update:step-is-valid']);
const { draftData, resolver, isValid, updateValue } = useDraftStep(
    zDocumentSubmissionSubmissionAssessmentAliasedData,
    'document_submission_submission_assessment',
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
                    draftData?.document_submission_process?.aliased_data
                        ?.submission_type
                "
                graph-slug="document_submission"
                node-alias="submission_type"
                @update:value="
                    updateValue(
                        $event,
                        'submission_type',
                        'document_submission_process',
                    )
                "
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.document_submission_process?.aliased_data
                        ?.submission_number
                "
                graph-slug="document_submission"
                node-alias="submission_number"
                @update:value="
                    updateValue(
                        $event,
                        'submission_number',
                        'document_submission_process',
                    )
                "
            />
        </FieldSet>
    </Form>
    <br />
</template>
