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
        'permit_scope',
        emit,
    );

const stockpilePlanRequired = computed(
    () =>
        typedDraftData.value?.permit_scope?.aliased_data
            ?.permit_scope_alteration?.aliased_data?.stockpile_plan_required
            ?.node_value,
);

defineExpose({ isValid });
</script>

<template>
    <Form
        :validate-on-blur="true"
        :validate-on-value-update="true"
        :validate-on-mount="false"
    >
        <FieldSet legend="Impact Management">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.permit_scope?.aliased_data
                        ?.permit_scope_alteration?.aliased_data
                        ?.impact_management_approach
                "
                graph-slug="hca_permit_application"
                node-alias="impact_management_approach"
                @update:aliased-node-data="
                    updateValue($event, 'impact_management_approach', [
                        'permit_scope',
                        'permit_scope_alteration',
                    ])
                "
            />
        </FieldSet>

        <FieldSet legend="Stockpile Plan">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.permit_scope?.aliased_data
                        ?.permit_scope_alteration?.aliased_data
                        ?.stockpile_plan_required
                "
                graph-slug="hca_permit_application"
                node-alias="stockpile_plan_required"
                @update:aliased-node-data="
                    updateValue($event, 'stockpile_plan_required', [
                        'permit_scope',
                        'permit_scope_alteration',
                    ])
                "
            />
            <GenericWidget
                v-if="stockpilePlanRequired === true"
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.permit_scope?.aliased_data
                        ?.permit_scope_alteration?.aliased_data
                        ?.stockpile_plan_approach
                "
                graph-slug="hca_permit_application"
                node-alias="stockpile_plan_approach"
                @update:aliased-node-data="
                    updateValue($event, 'stockpile_plan_approach', [
                        'permit_scope',
                        'permit_scope_alteration',
                    ])
                "
            />
        </FieldSet>

        <FieldSet legend="Additional Comments">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.permit_scope?.aliased_data
                        ?.permit_scope_alteration?.aliased_data
                        ?.impact_management_additional_comments
                "
                graph-slug="hca_permit_application"
                node-alias="impact_management_additional_comments"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'impact_management_additional_comments',
                        ['permit_scope', 'permit_scope_alteration'],
                    )
                "
            />
        </FieldSet>
    </Form>
</template>
