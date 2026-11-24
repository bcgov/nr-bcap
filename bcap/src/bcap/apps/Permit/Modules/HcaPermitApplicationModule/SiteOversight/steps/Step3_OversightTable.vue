<script setup lang="ts">
import { computed } from 'vue';
import { Form } from '@primevue/forms';
import MultiSelect from 'primevue/multiselect';
import GenericWidget from '@/arches_vue_components/generics/GenericWidget/GenericWidget.vue';
import { EDIT } from '@/arches_vue_components/widgets/constants.ts';
import FieldSet from 'primevue/fieldset';
import { useDraftStep } from '@/bcap/composables/useDraftStep.ts';
import type { HcaPermitApplicationResourceAliasedData } from '@/bcap/client/types.gen.ts';
import type { AliasedNodeData } from '@/arches_vue_components/types.ts';

const CULTURAL_AREAS = [
    {
        uri: 'https://localhost/bcap/ee010002-0000-4000-8000-000000000002',
        label: 'Northwest Coast',
    },
    {
        uri: 'https://localhost/bcap/ee010003-0000-4000-8000-000000000003',
        label: 'Interior Plateau',
    },
    {
        uri: 'https://localhost/bcap/ee010004-0000-4000-8000-000000000004',
        label: 'Sub-Arctic / Boreal Forest',
    },
];

const emit = defineEmits(['update:step-is-valid']);

const { draftData, typedDraftData, isValid, updateValue } =
    useDraftStep<HcaPermitApplicationResourceAliasedData>(
        undefined,
        'personnel',
        emit,
    );

const tiles = computed(
    () =>
        typedDraftData.value?.personnel?.aliased_data
            ?.assessment_oversight_responsibility ?? [],
);

const selectedAreaUris = computed(() =>
    tiles.value
        .map((t) => t.aliased_data?.cultural_area?.node_value?.[0]?.uri)
        .filter((uri): uri is string => !!uri),
);

function areaLabel(uri: string): string {
    return CULTURAL_AREAS.find((a) => a.uri === uri)?.label ?? uri;
}

function onSelectionChange(newUris: string[]) {
    const currentTiles = tiles.value;

    const newTiles = newUris.map((uri) => {
        const existing = currentTiles.find(
            (t) => t.aliased_data?.cultural_area?.node_value?.[0]?.uri === uri,
        );
        if (existing) return existing;

        const area = CULTURAL_AREAS.find((a) => a.uri === uri)!;
        return {
            aliased_data: {
                cultural_area: {
                    node_value: [
                        {
                            uri,
                            labels: [{ value: area.label, language_id: 'en' }],
                        },
                    ],
                    display_value: area.label,
                },
            },
        };
    });

    updateValue(
        newTiles as unknown as AliasedNodeData,
        'assessment_oversight_responsibility',
        'personnel',
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
        <FieldSet legend="Assessment Oversight by Cultural Area">
            <MultiSelect
                :model-value="selectedAreaUris"
                :options="CULTURAL_AREAS"
                option-label="label"
                option-value="uri"
                placeholder="Select cultural areas"
                display="chip"
                @update:model-value="onSelectionChange"
            />
            <div
                v-for="(tile, index) in tiles"
                :key="
                    tile.aliased_data?.cultural_area?.node_value?.[0]?.uri ??
                    index
                "
            >
                <FieldSet
                    :legend="
                        areaLabel(
                            tile.aliased_data?.cultural_area?.node_value?.[0]
                                ?.uri ?? '',
                        )
                    "
                >
                    <GenericWidget
                        :mode="EDIT"
                        :aliased-node-data="
                            draftData?.personnel?.aliased_data
                                ?.assessment_oversight_responsibility?.[index]
                                ?.aliased_data?.responsible_person
                        "
                        graph-slug="hca_permit_application"
                        node-alias="responsible_person"
                        @update:aliased-node-data="
                            updateValue($event, 'responsible_person', [
                                'personnel',
                                `assessment_oversight_responsibility[${index}]`,
                            ])
                        "
                    />
                    <GenericWidget
                        :mode="EDIT"
                        :aliased-node-data="
                            draftData?.personnel?.aliased_data
                                ?.assessment_oversight_responsibility?.[index]
                                ?.aliased_data?.responsibility_role
                        "
                        graph-slug="hca_permit_application"
                        node-alias="responsibility_role"
                        @update:aliased-node-data="
                            updateValue($event, 'responsibility_role', [
                                'personnel',
                                `assessment_oversight_responsibility[${index}]`,
                            ])
                        "
                    />
                </FieldSet>
            </div>
        </FieldSet>
    </Form>
</template>
