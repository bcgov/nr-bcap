<script setup lang="ts">
import { Form } from '@primevue/forms';
import { zInvestigationSection7RepositoryAndCurationAliasedData } from '@/bcap/client/zod.gen.ts';
import GenericWidget from '@/arches_vue_components/generics/GenericWidget/GenericWidget.vue';
import { EDIT } from '@/arches_vue_components/widgets/constants.ts';
import FieldSet from 'primevue/fieldset';
import { useDraftStep } from '@/bcap/composables/useDraftStep.ts';

const emit = defineEmits(['update:step-is-valid']);
const { draftData, resolver, isValid, updateValue } = useDraftStep(
    zInvestigationSection7RepositoryAndCurationAliasedData,
    'section_7_repository_and_curation',
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
                    draftData?.section_7_repository_and_curation?.aliased_data
                        ?.has_repository_been_contacted
                "
                graph-slug="investigation"
                node-alias="has_repository_been_contacted"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'has_repository_been_contacted',
                        'section_7_repository_and_curation',
                    )
                "
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.section_7_repository_and_curation?.aliased_data
                        ?.has_repository_agreement
                "
                graph-slug="investigation"
                node-alias="has_repository_agreement"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'has_repository_agreement',
                        'section_7_repository_and_curation',
                    )
                "
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.section_7_repository_and_curation?.aliased_data
                        ?.is_repository_required
                "
                graph-slug="investigation"
                node-alias="is_repository_required"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'is_repository_required',
                        'section_7_repository_and_curation',
                    )
                "
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.section_7_repository_and_curation?.aliased_data
                        ?.destination_repository
                "
                graph-slug="investigation"
                node-alias="destination_repository"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'destination_repository',
                        'section_7_repository_and_curation',
                    )
                "
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.section_7_repository_and_curation?.aliased_data
                        ?.additional_repository_and_curation_comments
                "
                graph-slug="investigation"
                node-alias="additional_repository_and_curation_comments"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'additional_repository_and_curation_comments',
                        'section_7_repository_and_curation',
                    )
                "
            />
        </FieldSet>
    </Form>
    <br />
</template>

<style></style>
