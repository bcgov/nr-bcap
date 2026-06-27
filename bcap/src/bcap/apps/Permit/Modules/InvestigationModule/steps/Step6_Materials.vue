<script setup lang="ts">
import { Form } from '@primevue/forms';
import { zInvestigationMaterialCollectionAliasedData } from '@/bcap/client/zod.gen.ts';
import GenericWidget from '@/arches_component_lab/generics/GenericWidget/GenericWidget.vue';
import { EDIT } from '@/arches_component_lab/widgets/constants.ts';
import FieldSet from 'primevue/fieldset';
import { useDraftStep } from '@/bcap/composables/useDraftStep.ts';

const emit = defineEmits(['update:step-is-valid']);
const { draftData, resolver, isValid, updateValue } = useDraftStep(
    'investigation',
    zInvestigationMaterialCollectionAliasedData,
    'material_collection',
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
                    draftData?.material_collection?.aliased_data
                        ?.collection_approach_details
                "
                graph-slug="investigation"
                node-alias="collection_approach_details"
                @update:value="
                    updateValue(
                        $event,
                        'collection_approach_details',
                        'material_collection',
                    )
                "
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.material_collection?.aliased_data
                        ?.collection_approach
                "
                graph-slug="investigation"
                node-alias="collection_approach"
                @update:value="
                    updateValue(
                        $event,
                        'collection_approach',
                        'material_collection',
                    )
                "
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.material_collection?.aliased_data
                        ?.details_of_collected_materials
                "
                graph-slug="investigation"
                node-alias="details_of_collected_materials"
                @update:value="
                    updateValue(
                        $event,
                        'details_of_collected_materials',
                        'material_collection',
                    )
                "
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.material_collection?.aliased_data
                        ?.collection_approach_additional_comments
                "
                graph-slug="investigation"
                node-alias="collection_approach_additional_comments"
                @update:value="
                    updateValue(
                        $event,
                        'collection_approach_additional_comments',
                        'material_collection',
                    )
                "
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.material_collection?.aliased_data
                        ?.details_of_collected_samples
                "
                graph-slug="investigation"
                node-alias="details_of_collected_samples"
                @update:value="
                    updateValue(
                        $event,
                        'details_of_collected_samples',
                        'material_collection',
                    )
                "
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.material_collection?.aliased_data
                        ?.additional_collection_and_sampling_details
                "
                graph-slug="investigation"
                node-alias="additional_collection_and_sampling_details"
                @update:value="
                    updateValue(
                        $event,
                        'additional_collection_and_sampling_details',
                        'material_collection',
                    )
                "
            />
        </FieldSet>
    </Form>
    <br />
</template>

<style></style>
