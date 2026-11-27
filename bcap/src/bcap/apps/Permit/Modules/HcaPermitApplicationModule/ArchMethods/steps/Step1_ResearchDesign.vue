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

const methodsNonAlignmentVisible = computed(
    () =>
        typedDraftData.value?.methodology?.aliased_data?.confirms_methods_align
            ?.node_value === false,
);
const preFieldResearchNonAlignmentVisible = computed(
    () =>
        typedDraftData.value?.methodology?.aliased_data
            ?.confirms_pre_field_research_aligns?.node_value === false,
);

defineExpose({ isValid });
</script>

<template>
    <Form
        :validate-on-blur="true"
        :validate-on-value-update="true"
        :validate-on-mount="false"
    >
        <FieldSet legend="Research Design">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.methodology?.aliased_data?.confirms_methods_align
                "
                graph-slug="hca_permit_application"
                node-alias="confirms_methods_align"
                @update:aliased-node-data="
                    updateValue($event, 'confirms_methods_align', 'methodology')
                "
            />
            <GenericWidget
                v-if="methodsNonAlignmentVisible"
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.methodology?.aliased_data?.methods_non_alignment
                "
                graph-slug="hca_permit_application"
                node-alias="methods_non_alignment"
                @update:aliased-node-data="
                    updateValue($event, 'methods_non_alignment', 'methodology')
                "
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.methodology?.aliased_data?.research_design
                "
                graph-slug="hca_permit_application"
                node-alias="research_design"
                @update:aliased-node-data="
                    updateValue($event, 'research_design', 'methodology')
                "
            />
        </FieldSet>

        <FieldSet legend="Pre-Field Research">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.methodology?.aliased_data
                        ?.confirms_pre_field_research_aligns
                "
                graph-slug="hca_permit_application"
                node-alias="confirms_pre_field_research_aligns"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'confirms_pre_field_research_aligns',
                        'methodology',
                    )
                "
            />
            <GenericWidget
                v-if="preFieldResearchNonAlignmentVisible"
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.methodology?.aliased_data
                        ?.pre_field_research_non_alignment
                "
                graph-slug="hca_permit_application"
                node-alias="pre_field_research_non_alignment"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'pre_field_research_non_alignment',
                        'methodology',
                    )
                "
            />
        </FieldSet>
    </Form>
</template>
