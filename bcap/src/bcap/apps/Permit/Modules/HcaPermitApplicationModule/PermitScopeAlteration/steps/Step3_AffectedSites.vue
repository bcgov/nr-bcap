<script setup lang="ts">
import { computed } from 'vue';
import { Form } from '@primevue/forms';
import GenericWidget from '@/arches_vue_components/generics/GenericWidget/GenericWidget.vue';
import { EDIT } from '@/arches_vue_components/widgets/constants.ts';
import FieldSet from 'primevue/fieldset';
import { useDraftStep } from '@/bcap/composables/useDraftStep.ts';
import type {
    HcaPermitApplicationResourceAliasedData,
    HcaPermitApplicationAffectedArchaeologicalSiteTile,
} from '@/bcap/client/types.gen.ts';
import type { AliasedNodeData } from '@/arches_vue_components/types.ts';

const emit = defineEmits(['update:step-is-valid']);

const { draftData, typedDraftData, isValid, updateValue } =
    useDraftStep<HcaPermitApplicationResourceAliasedData>(
        undefined,
        'permit_scope',
        emit,
    );

const affectedSitesTiles = computed(
    () =>
        typedDraftData.value?.permit_scope?.aliased_data
            ?.permit_scope_alteration?.aliased_data
            ?.affected_archaeological_site ?? [],
);

function addSiteRow() {
    const current =
        affectedSitesTiles.value as HcaPermitApplicationAffectedArchaeologicalSiteTile[];
    updateValue(
        [...current, { aliased_data: {} }] as unknown as AliasedNodeData,
        'affected_archaeological_site',
        ['permit_scope', 'permit_scope_alteration'],
    );
}

function removeSiteRow(index: number) {
    const current =
        affectedSitesTiles.value as HcaPermitApplicationAffectedArchaeologicalSiteTile[];
    const updated = [...current.slice(0, index), ...current.slice(index + 1)];
    updateValue(
        updated as unknown as AliasedNodeData,
        'affected_archaeological_site',
        ['permit_scope', 'permit_scope_alteration'],
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
        <FieldSet legend="Affected Archaeological Sites (Table 1)">
            <div
                v-for="(_, index) in affectedSitesTiles"
                :key="index"
            >
                <FieldSet :legend="`Site ${index + 1}`">
                    <GenericWidget
                        :mode="EDIT"
                        :aliased-node-data="
                            draftData?.permit_scope?.aliased_data
                                ?.permit_scope_alteration?.aliased_data
                                ?.affected_archaeological_site?.[index]
                                ?.aliased_data?.affected_archaeological_site
                        "
                        graph-slug="hca_permit_application"
                        node-alias="affected_archaeological_site"
                        @update:aliased-node-data="
                            updateValue(
                                $event,
                                'affected_archaeological_site',
                                [
                                    'permit_scope',
                                    'permit_scope_alteration',
                                    `affected_archaeological_site[${index}]`,
                                ],
                            )
                        "
                    />
                    <GenericWidget
                        :mode="EDIT"
                        :aliased-node-data="
                            draftData?.permit_scope?.aliased_data
                                ?.permit_scope_alteration?.aliased_data
                                ?.affected_archaeological_site?.[index]
                                ?.aliased_data?.anticipated_impacts
                        "
                        graph-slug="hca_permit_application"
                        node-alias="anticipated_impacts"
                        @update:aliased-node-data="
                            updateValue($event, 'anticipated_impacts', [
                                'permit_scope',
                                'permit_scope_alteration',
                                `affected_archaeological_site[${index}]`,
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
