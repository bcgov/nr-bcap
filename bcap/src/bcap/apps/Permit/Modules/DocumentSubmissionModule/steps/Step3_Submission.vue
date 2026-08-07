<script setup lang="ts">
import { ref } from 'vue';
import { Form } from '@primevue/forms';
import { zDocumentSubmissionReportSubmissionAliasedData } from '@/bcap/client/zod.gen.ts';
import GenericWidget from '@/arches_component_lab/generics/GenericWidget/GenericWidget.vue';
import { EDIT } from '@/arches_component_lab/widgets/constants.ts';
import FieldSet from 'primevue/fieldset';
import { useDraftStep } from '@/bcap/composables/useDraftStep.ts';

const emit = defineEmits(['update:step-is-valid']);

const { draftData, resolver, isValid, updateValue } = useDraftStep(
    zDocumentSubmissionReportSubmissionAliasedData,
    'report_submission',
    emit,
);

const initialFileState = ref(
    draftData.value?.report_submission?.aliased_data?.report_file,
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
        <FieldSet legend="Document Submission">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="initialFileState"
                graph-slug="document_submission"
                node-alias="report_file"
                @update:value="
                    updateValue($event, 'report_file', 'report_submission')
                "
            />

            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.report_submission?.aliased_data?.report_title
                "
                graph-slug="document_submission"
                node-alias="report_title"
                @update:value="
                    updateValue($event, 'report_title', 'report_submission')
                "
            />

            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.report_submission?.aliased_data
                        ?.archaeological_consultant
                "
                graph-slug="document_submission"
                node-alias="archaeological_consultant"
                @update:value="
                    updateValue(
                        $event,
                        'archaeological_consultant',
                        'report_submission',
                    )
                "
            />

            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.report_submission?.aliased_data
                        ?.consultant_report_number
                "
                graph-slug="document_submission"
                node-alias="consultant_report_number"
                @update:value="
                    updateValue(
                        $event,
                        'consultant_report_number',
                        'report_submission',
                    )
                "
            />

            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.report_submission?.aliased_data
                        ?.archaological_company
                "
                graph-slug="document_submission"
                node-alias="archaological_company"
                @update:value="
                    updateValue(
                        $event,
                        'archaological_company',
                        'report_submission',
                    )
                "
            />

            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.report_submission?.aliased_data
                        ?.report_recommendations
                "
                graph-slug="document_submission"
                node-alias="report_recommendations"
                @update:value="
                    updateValue(
                        $event,
                        'report_recommendations',
                        'report_submission',
                    )
                "
            />
        </FieldSet>
    </Form>
    <br />
</template>
