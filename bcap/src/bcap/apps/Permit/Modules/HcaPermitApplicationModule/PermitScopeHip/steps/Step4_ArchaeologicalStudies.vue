<script setup lang="ts">
import { computed } from 'vue';
import { Form } from '@primevue/forms';
import GenericWidget from '@/arches_vue_components/generics/GenericWidget/GenericWidget.vue';
import { EDIT } from '@/arches_vue_components/widgets/constants.ts';
import FieldSet from 'primevue/fieldset';
import { useDraftStep } from '@/bcap/composables/useDraftStep.ts';
import type {
    HcaPermitApplicationResourceAliasedData,
    HcaPermitApplicationHipPreviousStudiesTile,
    HcaPermitApplicationHipRecordedArchaeologicalSitesTile,
} from '@/bcap/client/types.gen.ts';
import type { AliasedNodeData } from '@/arches_vue_components/types.ts';

const emit = defineEmits(['update:step-is-valid']);

const { draftData, typedDraftData, isValid, updateValue } =
    useDraftStep<HcaPermitApplicationResourceAliasedData>(
        undefined,
        'permit_scope',
        emit,
    );

const hasAoa = computed(
    () =>
        typedDraftData.value?.permit_scope?.aliased_data?.permit_scope_hip
            ?.aliased_data?.hip_has_aoa?.node_value,
);

const hasPredictiveModel = computed(
    () =>
        typedDraftData.value?.permit_scope?.aliased_data?.permit_scope_hip
            ?.aliased_data?.hip_has_predictive_model?.node_value,
);

const previousStudiesTiles = computed(
    () =>
        typedDraftData.value?.permit_scope?.aliased_data?.permit_scope_hip
            ?.aliased_data?.hip_previous_studies ?? [],
);

const recordedSitesTiles = computed(
    () =>
        typedDraftData.value?.permit_scope?.aliased_data?.permit_scope_hip
            ?.aliased_data?.hip_recorded_archaeological_sites ?? [],
);

function addStudyRow() {
    const current =
        previousStudiesTiles.value as HcaPermitApplicationHipPreviousStudiesTile[];
    updateValue(
        [...current, { aliased_data: {} }] as unknown as AliasedNodeData,
        'hip_previous_studies',
        ['permit_scope', 'permit_scope_hip'],
    );
}

function removeStudyRow(index: number) {
    const current =
        previousStudiesTiles.value as HcaPermitApplicationHipPreviousStudiesTile[];
    const updated = [...current.slice(0, index), ...current.slice(index + 1)];
    updateValue(updated as unknown as AliasedNodeData, 'hip_previous_studies', [
        'permit_scope',
        'permit_scope_hip',
    ]);
}

function addSiteRow() {
    const current =
        recordedSitesTiles.value as HcaPermitApplicationHipRecordedArchaeologicalSitesTile[];
    updateValue(
        [...current, { aliased_data: {} }] as unknown as AliasedNodeData,
        'hip_recorded_archaeological_sites',
        ['permit_scope', 'permit_scope_hip'],
    );
}

function removeSiteRow(index: number) {
    const current =
        recordedSitesTiles.value as HcaPermitApplicationHipRecordedArchaeologicalSitesTile[];
    const updated = [...current.slice(0, index), ...current.slice(index + 1)];
    updateValue(
        updated as unknown as AliasedNodeData,
        'hip_recorded_archaeological_sites',
        ['permit_scope', 'permit_scope_hip'],
    );
}

defineExpose({ isValid });
</script>

<template>
    <Form
        :validate-on-blur="true"
        :validate-on-value-update="true"
        :validate-on-mount="false"
    >
        <FieldSet legend="Studies Present">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.permit_scope?.aliased_data?.permit_scope_hip
                        ?.aliased_data?.hip_has_aoa
                "
                graph-slug="hca_permit_application"
                node-alias="hip_has_aoa"
                @update:aliased-node-data="
                    updateValue($event, 'hip_has_aoa', [
                        'permit_scope',
                        'permit_scope_hip',
                    ])
                "
            />
            <template v-if="hasAoa === true">
                <GenericWidget
                    :mode="EDIT"
                    :aliased-node-data="
                        draftData?.permit_scope?.aliased_data?.permit_scope_hip
                            ?.aliased_data?.hip_has_predictive_model
                    "
                    graph-slug="hca_permit_application"
                    node-alias="hip_has_predictive_model"
                    @update:aliased-node-data="
                        updateValue($event, 'hip_has_predictive_model', [
                            'permit_scope',
                            'permit_scope_hip',
                        ])
                    "
                />
                <GenericWidget
                    v-if="hasPredictiveModel === true"
                    :mode="EDIT"
                    :aliased-node-data="
                        draftData?.permit_scope?.aliased_data?.permit_scope_hip
                            ?.aliased_data?.hip_predictive_model_name
                    "
                    graph-slug="hca_permit_application"
                    node-alias="hip_predictive_model_name"
                    @update:aliased-node-data="
                        updateValue($event, 'hip_predictive_model_name', [
                            'permit_scope',
                            'permit_scope_hip',
                        ])
                    "
                />
                <GenericWidget
                    :mode="EDIT"
                    :aliased-node-data="
                        draftData?.permit_scope?.aliased_data?.permit_scope_hip
                            ?.aliased_data?.hip_has_desk_based_assessment
                    "
                    graph-slug="hca_permit_application"
                    node-alias="hip_has_desk_based_assessment"
                    @update:aliased-node-data="
                        updateValue($event, 'hip_has_desk_based_assessment', [
                            'permit_scope',
                            'permit_scope_hip',
                        ])
                    "
                />
                <GenericWidget
                    :mode="EDIT"
                    :aliased-node-data="
                        draftData?.permit_scope?.aliased_data?.permit_scope_hip
                            ?.aliased_data?.hip_was_hip_aoa_permitted
                    "
                    graph-slug="hca_permit_application"
                    node-alias="hip_was_hip_aoa_permitted"
                    @update:aliased-node-data="
                        updateValue($event, 'hip_was_hip_aoa_permitted', [
                            'permit_scope',
                            'permit_scope_hip',
                        ])
                    "
                />
            </template>
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.permit_scope?.aliased_data?.permit_scope_hip
                        ?.aliased_data?.hip_has_field_studies
                "
                graph-slug="hca_permit_application"
                node-alias="hip_has_field_studies"
                @update:aliased-node-data="
                    updateValue($event, 'hip_has_field_studies', [
                        'permit_scope',
                        'permit_scope_hip',
                    ])
                "
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.permit_scope?.aliased_data?.permit_scope_hip
                        ?.aliased_data?.hip_has_other_studies
                "
                graph-slug="hca_permit_application"
                node-alias="hip_has_other_studies"
                @update:aliased-node-data="
                    updateValue($event, 'hip_has_other_studies', [
                        'permit_scope',
                        'permit_scope_hip',
                    ])
                "
            />
        </FieldSet>

        <FieldSet legend="Previous Studies (Table 2)">
            <div
                v-for="(_, index) in previousStudiesTiles"
                :key="index"
            >
                <FieldSet :legend="`Study ${index + 1}`">
                    <GenericWidget
                        :mode="EDIT"
                        :aliased-node-data="
                            draftData?.permit_scope?.aliased_data
                                ?.permit_scope_hip?.aliased_data
                                ?.hip_previous_studies?.[index]?.aliased_data
                                ?.hip_study_title
                        "
                        graph-slug="hca_permit_application"
                        node-alias="hip_study_title"
                        @update:aliased-node-data="
                            updateValue($event, 'hip_study_title', [
                                'permit_scope',
                                'permit_scope_hip',
                                `hip_previous_studies[${index}]`,
                            ])
                        "
                    />
                    <GenericWidget
                        :mode="EDIT"
                        :aliased-node-data="
                            draftData?.permit_scope?.aliased_data
                                ?.permit_scope_hip?.aliased_data
                                ?.hip_previous_studies?.[index]?.aliased_data
                                ?.hip_study_proximity_m
                        "
                        graph-slug="hca_permit_application"
                        node-alias="hip_study_proximity_m"
                        @update:aliased-node-data="
                            updateValue($event, 'hip_study_proximity_m', [
                                'permit_scope',
                                'permit_scope_hip',
                                `hip_previous_studies[${index}]`,
                            ])
                        "
                    />
                    <GenericWidget
                        :mode="EDIT"
                        :aliased-node-data="
                            draftData?.permit_scope?.aliased_data
                                ?.permit_scope_hip?.aliased_data
                                ?.hip_previous_studies?.[index]?.aliased_data
                                ?.hip_study_year
                        "
                        graph-slug="hca_permit_application"
                        node-alias="hip_study_year"
                        @update:aliased-node-data="
                            updateValue($event, 'hip_study_year', [
                                'permit_scope',
                                'permit_scope_hip',
                                `hip_previous_studies[${index}]`,
                            ])
                        "
                    />
                    <GenericWidget
                        :mode="EDIT"
                        :aliased-node-data="
                            draftData?.permit_scope?.aliased_data
                                ?.permit_scope_hip?.aliased_data
                                ?.hip_previous_studies?.[index]?.aliased_data
                                ?.hip_study_comments
                        "
                        graph-slug="hca_permit_application"
                        node-alias="hip_study_comments"
                        @update:aliased-node-data="
                            updateValue($event, 'hip_study_comments', [
                                'permit_scope',
                                'permit_scope_hip',
                                `hip_previous_studies[${index}]`,
                            ])
                        "
                    />
                    <button
                        type="button"
                        class="bc-remove-row"
                        @click="removeStudyRow(index)"
                    >
                        Remove
                    </button>
                </FieldSet>
            </div>
            <button
                type="button"
                class="bc-add-row"
                @click="addStudyRow"
            >
                Add Study
            </button>
        </FieldSet>

        <FieldSet legend="Previously Recorded Archaeological Sites (Table 3)">
            <div
                v-for="(_, index) in recordedSitesTiles"
                :key="index"
            >
                <FieldSet :legend="`Site ${index + 1}`">
                    <GenericWidget
                        :mode="EDIT"
                        :aliased-node-data="
                            draftData?.permit_scope?.aliased_data
                                ?.permit_scope_hip?.aliased_data
                                ?.hip_recorded_archaeological_sites?.[index]
                                ?.aliased_data?.hip_archaeological_site
                        "
                        graph-slug="hca_permit_application"
                        node-alias="hip_archaeological_site"
                        @update:aliased-node-data="
                            updateValue($event, 'hip_archaeological_site', [
                                'permit_scope',
                                'permit_scope_hip',
                                `hip_recorded_archaeological_sites[${index}]`,
                            ])
                        "
                    />
                    <button
                        type="button"
                        class="bc-remove-row"
                        @click="removeSiteRow(index)"
                    >
                        Remove
                    </button>
                </FieldSet>
            </div>
            <button
                type="button"
                class="bc-add-row"
                @click="addSiteRow"
            >
                Add Site
            </button>
        </FieldSet>
    </Form>
</template>
