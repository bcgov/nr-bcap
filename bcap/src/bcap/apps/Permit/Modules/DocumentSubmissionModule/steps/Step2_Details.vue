<script setup lang="ts">
import { Form } from '@primevue/forms';
import { zDocumentSubmissionDocumentSubmissionProcessAliasedData } from '@/bcap/client/zod.gen.ts';
import type { DocumentSubmissionResourceAliasedData } from '@/bcap/client/types.gen.ts';
import GenericWidget from '@/arches_vue_components/generics/GenericWidget/GenericWidget.vue';
import { EDIT } from '@/arches_vue_components/widgets/constants.ts';
import FieldSet from 'primevue/fieldset';
import { useDraftStep } from '@/bcap/composables/useDraftStep.ts';
import { onMounted } from 'vue';

const emit = defineEmits(['update:step-is-valid']);
const NODE_GROUP: keyof DocumentSubmissionResourceAliasedData =
    'document_submission_process';

const { draftData, resolver, isValid, updateValue } = useDraftStep(
    zDocumentSubmissionDocumentSubmissionProcessAliasedData,
    NODE_GROUP,
    emit,
);

defineExpose({ isValid });

onMounted(() => {
    emit('update:step-is-valid', isValid());
});
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
                @update:aliased-node-data="
                    updateValue($event, 'submission_type', NODE_GROUP)
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
                @update:aliased-node-data="
                    updateValue($event, 'submission_number', NODE_GROUP)
                "
            />
        </FieldSet>
    </Form>
    <br />
</template>
