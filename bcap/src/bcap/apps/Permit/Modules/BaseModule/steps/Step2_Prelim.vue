<script setup lang="ts">
import { Form } from '@primevue/forms';
import { zPermitApplicationApplicationIdentificationAliasedData } from '@/bcap/client/zod.gen.ts';
import GenericWidget from '@/arches_vue_components/generics/GenericWidget/GenericWidget.vue';
import { EDIT } from '@/arches_vue_components/widgets/constants.ts';
import FieldSet from 'primevue/fieldset';
import { useDraftStep } from '@/bcap/composables/useDraftStep.ts';

const emit = defineEmits(['update:step-is-valid']);

// use draft not form state, this is different than bcfms/bcrhp
const { draftData, resolver, isValid, updateValue } = useDraftStep(
    zPermitApplicationApplicationIdentificationAliasedData,
    'application_identification',
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
                    draftData?.application_identification?.aliased_data
                        ?.filing_type
                "
                graph-slug="permit_application"
                node-alias="filing_type"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'filing_type',
                        'application_identification',
                    )
                "
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.application_identification?.aliased_data
                        ?.project_name
                "
                graph-slug="permit_application"
                node-alias="project_name"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'project_name',
                        'application_identification',
                    )
                "
            />
            <GenericWidget
                class="description-box"
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.proposed_project?.aliased_data
                        ?.project_description
                "
                graph-slug="permit_application"
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
                graph-slug="permit_application"
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
