<script setup lang="ts">
import { Form } from '@primevue/forms';
import { zInvestigationSection6AncestralRemainsAliasedData } from '@/bcap/client/zod.gen.ts';
import GenericWidget from '@/arches_component_lab/generics/GenericWidget/GenericWidget.vue';
import { EDIT } from '@/arches_component_lab/widgets/constants.ts';
import FieldSet from 'primevue/fieldset';
import { useDraftStep } from '@/bcap/composables/useDraftStep.ts';

const emit = defineEmits(['update:step-is-valid']);
const { draftData, resolver, isValid, updateValue } = useDraftStep(
    'investigation',
    zInvestigationSection6AncestralRemainsAliasedData,
    'section_6_ancestral_remains',
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
                    draftData?.section_6_ancestral_remains?.aliased_data
                        ?.alternate_ancestral_remains_approach
                "
                graph-slug="investigation"
                node-alias="alternate_ancestral_remains_approach"
                @update:value="
                    updateValue(
                        $event,
                        'alternate_ancestral_remains_approach',
                        'section_6_ancestral_remains',
                    )
                "
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.section_6_ancestral_remains?.aliased_data
                        ?.ancestral_remains_approach_compliant
                "
                graph-slug="investigation"
                node-alias="ancestral_remains_approach_compliant"
                @update:value="
                    updateValue(
                        $event,
                        'ancestral_remains_approach_compliant',
                        'section_6_ancestral_remains',
                    )
                "
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.section_6_ancestral_remains?.aliased_data
                        ?.ancestral_remains_approach_methods
                "
                graph-slug="investigation"
                node-alias="ancestral_remains_approach_methods"
                @update:value="
                    updateValue(
                        $event,
                        'ancestral_remains_approach_methods',
                        'section_6_ancestral_remains',
                    )
                "
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.section_6_ancestral_remains?.aliased_data
                        ?.ancestral_remains_approach_additional_comments
                "
                graph-slug="investigation"
                node-alias="ancestral_remains_approach_additional_comments"
                @update:value="
                    updateValue(
                        $event,
                        'ancestral_remains_approach_additional_comments',
                        'section_6_ancestral_remains',
                    )
                "
            />
        </FieldSet>
    </Form>
    <br />
</template>

<style></style>
