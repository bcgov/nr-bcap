<script setup lang="ts">
import { computed } from 'vue';
import { Form } from '@primevue/forms';
import GenericWidget from '@/arches_vue_components/generics/GenericWidget/GenericWidget.vue';
import { EDIT } from '@/arches_vue_components/widgets/constants.ts';
import FieldSet from 'primevue/fieldset';
import { useDraftStep } from '@/bcap/composables/useDraftStep.ts';
import type {
    HcaPermitApplicationResourceAliasedData,
    HcaPermitApplicationRelatedAssessmentTile,
} from '@/bcap/client/types.gen.ts';
import type { AliasedNodeData } from '@/arches_vue_components/types.ts';

const emit = defineEmits(['update:step-is-valid']);

const { draftData, typedDraftData, isValid, updateValue } =
    useDraftStep<HcaPermitApplicationResourceAliasedData>(
        undefined,
        'permit_scope',
        emit,
    );

const relatedAssessmentTiles = computed(
    () =>
        typedDraftData.value?.permit_scope?.aliased_data
            ?.permit_scope_alteration?.aliased_data?.related_assessment ?? [],
);

function addAssessmentRow() {
    const current =
        relatedAssessmentTiles.value as HcaPermitApplicationRelatedAssessmentTile[];
    updateValue(
        [...current, { aliased_data: {} }] as unknown as AliasedNodeData,
        'related_assessment',
        ['permit_scope', 'permit_scope_alteration'],
    );
}

function removeAssessmentRow(index: number) {
    const current =
        relatedAssessmentTiles.value as HcaPermitApplicationRelatedAssessmentTile[];
    const updated = [...current.slice(0, index), ...current.slice(index + 1)];
    updateValue(updated as unknown as AliasedNodeData, 'related_assessment', [
        'permit_scope',
        'permit_scope_alteration',
    ]);
}

defineExpose({ isValid });
</script>

<template>
    <Form
        :validate-on-blur="true"
        :validate-on-value-update="true"
        :validate-on-mount="false"
    >
        <FieldSet legend="Related Assessments (Table 2)">
            <div
                v-for="(_, index) in relatedAssessmentTiles"
                :key="index"
            >
                <FieldSet :legend="`Assessment ${index + 1}`">
                    <GenericWidget
                        :mode="EDIT"
                        :aliased-node-data="
                            draftData?.permit_scope?.aliased_data
                                ?.permit_scope_alteration?.aliased_data
                                ?.related_assessment?.[index]?.aliased_data
                                ?.study_type
                        "
                        graph-slug="hca_permit_application"
                        node-alias="study_type"
                        @update:aliased-node-data="
                            updateValue($event, 'study_type', [
                                'permit_scope',
                                'permit_scope_alteration',
                                `related_assessment[${index}]`,
                            ])
                        "
                    />
                    <GenericWidget
                        :mode="EDIT"
                        :aliased-node-data="
                            draftData?.permit_scope?.aliased_data
                                ?.permit_scope_alteration?.aliased_data
                                ?.related_assessment?.[index]?.aliased_data
                                ?.hca_permit
                        "
                        graph-slug="hca_permit_application"
                        node-alias="hca_permit"
                        @update:aliased-node-data="
                            updateValue($event, 'hca_permit', [
                                'permit_scope',
                                'permit_scope_alteration',
                                `related_assessment[${index}]`,
                            ])
                        "
                    />
                    <GenericWidget
                        :mode="EDIT"
                        :aliased-node-data="
                            draftData?.permit_scope?.aliased_data
                                ?.permit_scope_alteration?.aliased_data
                                ?.related_assessment?.[index]?.aliased_data
                                ?.proposed_alteration_proximity
                        "
                        graph-slug="hca_permit_application"
                        node-alias="proposed_alteration_proximity"
                        @update:aliased-node-data="
                            updateValue(
                                $event,
                                'proposed_alteration_proximity',
                                [
                                    'permit_scope',
                                    'permit_scope_alteration',
                                    `related_assessment[${index}]`,
                                ],
                            )
                        "
                    />
                    <GenericWidget
                        :mode="EDIT"
                        :aliased-node-data="
                            draftData?.permit_scope?.aliased_data
                                ?.permit_scope_alteration?.aliased_data
                                ?.related_assessment?.[index]?.aliased_data
                                ?.assessment_year
                        "
                        graph-slug="hca_permit_application"
                        node-alias="assessment_year"
                        @update:aliased-node-data="
                            updateValue($event, 'assessment_year', [
                                'permit_scope',
                                'permit_scope_alteration',
                                `related_assessment[${index}]`,
                            ])
                        "
                    />
                    <GenericWidget
                        :mode="EDIT"
                        :aliased-node-data="
                            draftData?.permit_scope?.aliased_data
                                ?.permit_scope_alteration?.aliased_data
                                ?.related_assessment?.[index]?.aliased_data
                                ?.assessment_comments
                        "
                        graph-slug="hca_permit_application"
                        node-alias="assessment_comments"
                        @update:aliased-node-data="
                            updateValue($event, 'assessment_comments', [
                                'permit_scope',
                                'permit_scope_alteration',
                                `related_assessment[${index}]`,
                            ])
                        "
                    />
                    <button
                        type="button"
                        class="bc-remove-row"
                        @click="removeAssessmentRow(index)"
                    >
                        Remove
                    </button>
                </FieldSet>
            </div>
            <button
                type="button"
                class="bc-add-row"
                @click="addAssessmentRow"
            >
                Add Assessment
            </button>
        </FieldSet>

        <FieldSet legend="Previous Assessment Discussion">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.permit_scope?.aliased_data
                        ?.permit_scope_alteration?.aliased_data
                        ?.previous_assessment_discussion
                "
                graph-slug="hca_permit_application"
                node-alias="previous_assessment_discussion"
                @update:aliased-node-data="
                    updateValue($event, 'previous_assessment_discussion', [
                        'permit_scope',
                        'permit_scope_alteration',
                    ])
                "
            />
        </FieldSet>
    </Form>
</template>
