<script setup lang="ts">
import { Form } from '@primevue/forms';
import * as z from 'zod';
import { zReferenceAliasedNodeDataRequired } from '@/bcap/client/zod.gen.ts';
import GenericWidget from '@/arches_vue_components/generics/GenericWidget/GenericWidget.vue';
import { EDIT } from '@/arches_vue_components/widgets/constants.ts';
import FieldSet from 'primevue/fieldset';
import { useDraftStep } from '@/bcap/composables/useDraftStep.ts';

const emit = defineEmits(['update:step-is-valid']);

// Only service_request_type is user-fillable and required; service_request_id
// is backend-generated and must be excluded so isComplete() can return true.
const stepSchema = z.object({
    service_request_type: zReferenceAliasedNodeDataRequired,
});

// use draft not form state, this is different than bcfms/bcrhp
const { draftData, resolver, isValid, updateValue } = useDraftStep(
    stepSchema,
    'service_request_identification',
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
        <FieldSet legend="">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.service_request_identification?.aliased_data
                        ?.service_request_type
                "
                graph-slug="bcap_service_request"
                node-alias="service_request_type"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'service_request_type',
                        'service_request_identification',
                    )
                "
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.proposed_project?.aliased_data?.project_name
                "
                graph-slug="bcap_service_request"
                node-alias="project_name"
                @update:aliased-node-data="
                    updateValue($event, 'project_name', 'proposed_project')
                "
            />
            <GenericWidget
                class="description-box"
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.proposed_project?.aliased_data
                        ?.project_description
                "
                graph-slug="bcap_service_request"
                node-alias="project_description"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'project_description',
                        'proposed_project',
                    )
                "
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.proposed_project?.aliased_data?.scope_of_work
                "
                graph-slug="bcap_service_request"
                node-alias="scope_of_work"
                @update:aliased-node-data="
                    updateValue($event, 'scope_of_work', 'proposed_project')
                "
            />
        </FieldSet>
    </Form>
    <br />
</template>

<style scoped>
.row {
    display: flex;
    gap: 1rem;
    width: 100%;
}
.row > * {
    flex: 1;
}
</style>
