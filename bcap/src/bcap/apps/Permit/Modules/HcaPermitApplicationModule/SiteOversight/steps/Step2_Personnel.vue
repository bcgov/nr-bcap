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
        'personnel',
        emit,
    );

const hasDirectingArchaeologist = computed(
    () =>
        typedDraftData.value?.personnel?.aliased_data
            ?.has_directing_archaeologist?.node_value,
);

defineExpose({ isValid });
</script>

<template>
    <Form
        :validate-on-blur="true"
        :validate-on-value-update="true"
        :validate-on-mount="false"
    >
        <FieldSet legend="Site Oversight">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.personnel?.aliased_data
                        ?.has_directing_archaeologist
                "
                graph-slug="hca_permit_application"
                node-alias="has_directing_archaeologist"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'has_directing_archaeologist',
                        'personnel',
                    )
                "
            />
            <GenericWidget
                v-if="hasDirectingArchaeologist === true"
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.personnel?.aliased_data
                        ?.archaeologist_deliverables_role
                "
                graph-slug="hca_permit_application"
                node-alias="archaeologist_deliverables_role"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'archaeologist_deliverables_role',
                        'personnel',
                    )
                "
            />
            <GenericWidget
                v-if="hasDirectingArchaeologist === false"
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.personnel?.aliased_data
                        ?.applicant_responsibility_details
                "
                graph-slug="hca_permit_application"
                node-alias="applicant_responsibility_details"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'applicant_responsibility_details',
                        'personnel',
                    )
                "
            />
        </FieldSet>
        <FieldSet legend="Additional Comments">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.personnel?.aliased_data
                        ?.personnel_additional_comments
                "
                graph-slug="hca_permit_application"
                node-alias="personnel_additional_comments"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'personnel_additional_comments',
                        'personnel',
                    )
                "
            />
        </FieldSet>
    </Form>
</template>
