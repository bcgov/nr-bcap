<script setup lang="ts">
import { computed } from 'vue';
import { Form } from '@primevue/forms';
import GenericWidget from '@/arches_vue_components/generics/GenericWidget/GenericWidget.vue';
import { EDIT } from '@/arches_vue_components/widgets/constants.ts';
import FieldSet from 'primevue/fieldset';
import { useDraftStep } from '@/bcap/composables/useDraftStep.ts';
import type { HcaPermitApplicationResourceAliasedData } from '@/bcap/client/types.gen.ts';

const emit = defineEmits(['update:step-is-valid']);

const { draftData, typedDraftData, isValid, updateValue } =
    useDraftStep<HcaPermitApplicationResourceAliasedData>(
        undefined,
        'methodology',
        emit,
    );

const winterMethodsFieldsVisible = computed(
    () =>
        typedDraftData.value?.methodology?.aliased_data?.has_winter_methods
            ?.node_value === true,
);

defineExpose({ isValid });
</script>

<template>
    <Form
        :validate-on-blur="true"
        :validate-on-value-update="true"
        :validate-on-mount="false"
    >
        <FieldSet legend="Winter Methods">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.methodology?.aliased_data?.has_winter_methods
                "
                graph-slug="hca_permit_application"
                node-alias="has_winter_methods"
                @update:aliased-node-data="
                    updateValue($event, 'has_winter_methods', 'methodology')
                "
            />
            <GenericWidget
                v-if="winterMethodsFieldsVisible"
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.methodology?.aliased_data?.winter_methods_align
                "
                graph-slug="hca_permit_application"
                node-alias="winter_methods_align"
                @update:aliased-node-data="
                    updateValue($event, 'winter_methods_align', 'methodology')
                "
            />
            <GenericWidget
                v-if="winterMethodsFieldsVisible"
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.methodology?.aliased_data
                        ?.winter_methods_description
                "
                graph-slug="hca_permit_application"
                node-alias="winter_methods_description"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'winter_methods_description',
                        'methodology',
                    )
                "
            />
        </FieldSet>
    </Form>
</template>
