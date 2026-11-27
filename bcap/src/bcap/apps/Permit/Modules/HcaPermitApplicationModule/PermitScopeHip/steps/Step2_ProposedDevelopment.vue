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

const isSingleDevelopment = computed(() =>
    typedDraftData.value?.permit_scope?.aliased_data?.permit_scope_hip?.aliased_data?.hip_application_area_type?.node_value?.[0]?.uri?.includes(
        'ea010001',
    ),
);

const isMapApplication = computed(() =>
    typedDraftData.value?.permit_scope?.aliased_data?.permit_scope_hip?.aliased_data?.hip_application_area_type?.node_value?.[0]?.uri?.includes(
        'ea010002',
    ),
);

const addressesChanceFinds = computed(
    () =>
        typedDraftData.value?.permit_scope?.aliased_data?.permit_scope_hip
            ?.aliased_data?.hip_addresses_chance_finds?.node_value,
);

defineExpose({ isValid });
</script>

<template>
    <Form
        :validate-on-blur="true"
        :validate-on-value-update="true"
        :validate-on-mount="false"
    >
        <FieldSet legend="Project Type">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.permit_scope?.aliased_data?.permit_scope_hip
                        ?.aliased_data?.hip_project_type_ref
                "
                graph-slug="hca_permit_application"
                node-alias="hip_project_type_ref"
                @update:aliased-node-data="
                    updateValue($event, 'hip_project_type_ref', [
                        'permit_scope',
                        'permit_scope_hip',
                    ])
                "
            />
        </FieldSet>

        <FieldSet legend="Goals and Objectives">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.permit_scope?.aliased_data?.permit_scope_hip
                        ?.aliased_data?.hip_goals_and_objectives
                "
                graph-slug="hca_permit_application"
                node-alias="hip_goals_and_objectives"
                @update:aliased-node-data="
                    updateValue($event, 'hip_goals_and_objectives', [
                        'permit_scope',
                        'permit_scope_hip',
                    ])
                "
            />
        </FieldSet>

        <FieldSet legend="Assessment Area">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.permit_scope?.aliased_data?.permit_scope_hip
                        ?.aliased_data?.hip_application_area_type
                "
                graph-slug="hca_permit_application"
                node-alias="hip_application_area_type"
                @update:aliased-node-data="
                    updateValue($event, 'hip_application_area_type', [
                        'permit_scope',
                        'permit_scope_hip',
                    ])
                "
            />
            <GenericWidget
                v-if="isSingleDevelopment"
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.permit_scope?.aliased_data?.permit_scope_hip
                        ?.aliased_data?.hip_assessment_area_size_ha
                "
                graph-slug="hca_permit_application"
                node-alias="hip_assessment_area_size_ha"
                @update:aliased-node-data="
                    updateValue($event, 'hip_assessment_area_size_ha', [
                        'permit_scope',
                        'permit_scope_hip',
                    ])
                "
            />
            <GenericWidget
                v-if="isMapApplication"
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.permit_scope?.aliased_data?.permit_scope_hip
                        ?.aliased_data?.hip_development_selection
                "
                graph-slug="hca_permit_application"
                node-alias="hip_development_selection"
                @update:aliased-node-data="
                    updateValue($event, 'hip_development_selection', [
                        'permit_scope',
                        'permit_scope_hip',
                    ])
                "
            />
        </FieldSet>

        <FieldSet legend="Chance Finds">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.permit_scope?.aliased_data?.permit_scope_hip
                        ?.aliased_data?.hip_addresses_chance_finds
                "
                graph-slug="hca_permit_application"
                node-alias="hip_addresses_chance_finds"
                @update:aliased-node-data="
                    updateValue($event, 'hip_addresses_chance_finds', [
                        'permit_scope',
                        'permit_scope_hip',
                    ])
                "
            />
            <GenericWidget
                v-if="addressesChanceFinds === true"
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.permit_scope?.aliased_data?.permit_scope_hip
                        ?.aliased_data?.hip_chance_finds_details
                "
                graph-slug="hca_permit_application"
                node-alias="hip_chance_finds_details"
                @update:aliased-node-data="
                    updateValue($event, 'hip_chance_finds_details', [
                        'permit_scope',
                        'permit_scope_hip',
                    ])
                "
            />
        </FieldSet>
    </Form>
</template>
