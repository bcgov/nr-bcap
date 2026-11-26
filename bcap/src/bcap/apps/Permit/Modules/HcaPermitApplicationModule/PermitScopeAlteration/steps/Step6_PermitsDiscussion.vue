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

const hasRelatedPermits = computed(
    () =>
        typedDraftData.value?.permit_scope?.aliased_data
            ?.permit_scope_alteration?.aliased_data?.has_related_permits
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
        <FieldSet legend="Related Permits">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.permit_scope?.aliased_data
                        ?.permit_scope_alteration?.aliased_data
                        ?.has_related_permits
                "
                graph-slug="hca_permit_application"
                node-alias="has_related_permits"
                @update:aliased-node-data="
                    updateValue($event, 'has_related_permits', [
                        'permit_scope',
                        'permit_scope_alteration',
                    ])
                "
            />
            <GenericWidget
                v-if="hasRelatedPermits === true"
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.permit_scope?.aliased_data
                        ?.permit_scope_alteration?.aliased_data
                        ?.related_permits_description
                "
                graph-slug="hca_permit_application"
                node-alias="related_permits_description"
                @update:aliased-node-data="
                    updateValue($event, 'related_permits_description', [
                        'permit_scope',
                        'permit_scope_alteration',
                    ])
                "
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.permit_scope?.aliased_data
                        ?.permit_scope_alteration?.aliased_data
                        ?.related_permits_additional_comments
                "
                graph-slug="hca_permit_application"
                node-alias="related_permits_additional_comments"
                @update:aliased-node-data="
                    updateValue($event, 'related_permits_additional_comments', [
                        'permit_scope',
                        'permit_scope_alteration',
                    ])
                "
            />
        </FieldSet>

        <FieldSet legend="First Nation File Numbers">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.permit_scope?.aliased_data
                        ?.permit_scope_alteration?.aliased_data
                        ?.first_nation_file_numbers
                "
                graph-slug="hca_permit_application"
                node-alias="first_nation_file_numbers"
                @update:aliased-node-data="
                    updateValue($event, 'first_nation_file_numbers', [
                        'permit_scope',
                        'permit_scope_alteration',
                    ])
                "
            />
        </FieldSet>

        <FieldSet legend="Additional Discussion">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.permit_scope?.aliased_data
                        ?.permit_scope_alteration?.aliased_data
                        ?.additional_discussion
                "
                graph-slug="hca_permit_application"
                node-alias="additional_discussion"
                @update:aliased-node-data="
                    updateValue($event, 'additional_discussion', [
                        'permit_scope',
                        'permit_scope_alteration',
                    ])
                "
            />
        </FieldSet>
    </Form>
</template>
