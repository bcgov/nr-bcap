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

const surveyCoverageNonAlignmentVisible = computed(
    () =>
        typedDraftData.value?.methodology?.aliased_data
            ?.confirms_survey_coverage_aligns?.node_value === false,
);
const archPotentialNonAlignmentVisible = computed(
    () =>
        typedDraftData.value?.methodology?.aliased_data
            ?.confirms_arch_potential_aligns?.node_value === false,
);

defineExpose({ isValid });
</script>

<template>
    <Form
        :validate-on-blur="true"
        :validate-on-value-update="true"
        :validate-on-mount="false"
    >
        <FieldSet legend="Survey Coverage">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.methodology?.aliased_data
                        ?.confirms_survey_coverage_aligns
                "
                graph-slug="hca_permit_application"
                node-alias="confirms_survey_coverage_aligns"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'confirms_survey_coverage_aligns',
                        'methodology',
                    )
                "
            />
            <GenericWidget
                v-if="surveyCoverageNonAlignmentVisible"
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.methodology?.aliased_data
                        ?.survey_coverage_non_alignment
                "
                graph-slug="hca_permit_application"
                node-alias="survey_coverage_non_alignment"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'survey_coverage_non_alignment',
                        'methodology',
                    )
                "
            />
        </FieldSet>

        <FieldSet legend="Archaeological Potential">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.methodology?.aliased_data
                        ?.confirms_arch_potential_aligns
                "
                graph-slug="hca_permit_application"
                node-alias="confirms_arch_potential_aligns"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'confirms_arch_potential_aligns',
                        'methodology',
                    )
                "
            />
            <GenericWidget
                v-if="archPotentialNonAlignmentVisible"
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.methodology?.aliased_data
                        ?.arch_potential_non_alignment
                "
                graph-slug="hca_permit_application"
                node-alias="arch_potential_non_alignment"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'arch_potential_non_alignment',
                        'methodology',
                    )
                "
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.methodology?.aliased_data
                        ?.arch_bearing_sediment_approach
                "
                graph-slug="hca_permit_application"
                node-alias="arch_bearing_sediment_approach"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'arch_bearing_sediment_approach',
                        'methodology',
                    )
                "
            />
        </FieldSet>
    </Form>
</template>
