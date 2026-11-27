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

const subsurfaceTestingNonAlignmentVisible = computed(
    () =>
        typedDraftData.value?.methodology?.aliased_data
            ?.confirms_subsurface_testing_aligns?.node_value === false,
);

defineExpose({ isValid });
</script>

<template>
    <Form
        :validate-on-blur="true"
        :validate-on-value-update="true"
        :validate-on-mount="false"
    >
        <FieldSet legend="Subsurface Testing">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.methodology?.aliased_data
                        ?.confirms_subsurface_testing_aligns
                "
                graph-slug="hca_permit_application"
                node-alias="confirms_subsurface_testing_aligns"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'confirms_subsurface_testing_aligns',
                        'methodology',
                    )
                "
            />
            <GenericWidget
                v-if="subsurfaceTestingNonAlignmentVisible"
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.methodology?.aliased_data
                        ?.subsurface_testing_non_alignment
                "
                graph-slug="hca_permit_application"
                node-alias="subsurface_testing_non_alignment"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'subsurface_testing_non_alignment',
                        'methodology',
                    )
                "
            />
        </FieldSet>
    </Form>
</template>
