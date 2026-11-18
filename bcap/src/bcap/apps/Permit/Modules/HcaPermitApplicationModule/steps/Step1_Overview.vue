<script setup lang="ts">
import { computed } from 'vue';
import { Form } from '@primevue/forms';
import * as z from 'zod';
import { zNonLocalizedStringAliasedNodeData } from '@/bcap/client/zod.gen.ts';
import GenericWidget from '@/arches_vue_components/generics/GenericWidget/GenericWidget.vue';
import { EDIT } from '@/arches_vue_components/widgets/constants.ts';
import FieldSet from 'primevue/fieldset';
import { useDraftStep } from '@/bcap/composables/useDraftStep.ts';
import type { HcaPermitApplicationResourceAliasedData } from '@/bcap/client/types.gen.ts';

const emit = defineEmits(['update:step-is-valid']);

// permit_type and project_description are the minimum required fields.
const stepSchema = z.object({
    permit_type: zNonLocalizedStringAliasedNodeData,
    project_description: zNonLocalizedStringAliasedNodeData,
});

const { draftData, typedDraftData, resolver, isValid, updateValue } =
    useDraftStep<HcaPermitApplicationResourceAliasedData>(
        stepSchema,
        'application_overview',
        emit,
    );

const isReplacement = computed(
    () =>
        typedDraftData.value?.application_overview?.aliased_data
            ?.is_replacement_permit?.node_value === true,
);
const hasConcurrent = computed(
    () =>
        typedDraftData.value?.application_overview?.aliased_data
            ?.has_concurrent_permits?.node_value === true,
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
        <FieldSet legend="Permit Details">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.application_overview?.aliased_data?.permit_type
                "
                graph-slug="hca_permit_application"
                node-alias="permit_type"
                @update:aliased-node-data="
                    updateValue($event, 'permit_type', 'application_overview')
                "
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.application_overview?.aliased_data
                        ?.is_first_time_holder
                "
                graph-slug="hca_permit_application"
                node-alias="is_first_time_holder"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'is_first_time_holder',
                        'application_overview',
                    )
                "
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.application_overview?.aliased_data?.permit_term
                "
                graph-slug="hca_permit_application"
                node-alias="permit_term"
                @update:aliased-node-data="
                    updateValue($event, 'permit_term', 'application_overview')
                "
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.application_overview?.aliased_data
                        ?.deliverables_due_date_type
                "
                graph-slug="hca_permit_application"
                node-alias="deliverables_due_date_type"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'deliverables_due_date_type',
                        'application_overview',
                    )
                "
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.application_overview?.aliased_data?.sector
                "
                graph-slug="hca_permit_application"
                node-alias="sector"
                @update:aliased-node-data="
                    updateValue($event, 'sector', 'application_overview')
                "
            />
        </FieldSet>

        <FieldSet legend="Replacement Permit">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.application_overview?.aliased_data
                        ?.is_replacement_permit
                "
                graph-slug="hca_permit_application"
                node-alias="is_replacement_permit"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'is_replacement_permit',
                        'application_overview',
                    )
                "
            />
            <GenericWidget
                v-if="isReplacement"
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.application_overview?.aliased_data
                        ?.existing_permit_number
                "
                graph-slug="hca_permit_application"
                node-alias="existing_permit_number"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'existing_permit_number',
                        'application_overview',
                    )
                "
            />
        </FieldSet>

        <FieldSet legend="Concurrent Permits">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.application_overview?.aliased_data
                        ?.has_concurrent_permits
                "
                graph-slug="hca_permit_application"
                node-alias="has_concurrent_permits"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'has_concurrent_permits',
                        'application_overview',
                    )
                "
            />
            <GenericWidget
                v-if="hasConcurrent"
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.application_overview?.aliased_data
                        ?.concurrent_permit_numbers
                "
                graph-slug="hca_permit_application"
                node-alias="concurrent_permit_numbers"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'concurrent_permit_numbers',
                        'application_overview',
                    )
                "
            />
        </FieldSet>

        <FieldSet legend="Project Description">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.application_overview?.aliased_data
                        ?.project_description
                "
                graph-slug="hca_permit_application"
                node-alias="project_description"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'project_description',
                        'application_overview',
                    )
                "
            />
        </FieldSet>
    </Form>
</template>
