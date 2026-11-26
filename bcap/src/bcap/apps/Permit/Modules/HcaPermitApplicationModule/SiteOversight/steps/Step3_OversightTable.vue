<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { Form } from '@primevue/forms';
import MultiSelect from 'primevue/multiselect';
import GenericWidget from '@/arches_vue_components/generics/GenericWidget/GenericWidget.vue';
import { EDIT } from '@/arches_vue_components/widgets/constants.ts';
import FieldSet from 'primevue/fieldset';
import { useDraftStep } from '@/bcap/composables/useDraftStep.ts';
import { useReferenceSelectOptionsStore } from '@/arches_controlled_lists/stores/useReferenceSelectOptionsStore.ts';
import type { HcaPermitApplicationResourceAliasedData } from '@/bcap/client/types.gen.ts';
import type { AliasedNodeData } from '@/arches_vue_components/types.ts';
import type { ReferenceSelectTreeNode } from '@/arches_controlled_lists/datatypes/reference-select/types.ts';

const SITE_VISIT_FIELD_DIRECTOR_LABEL = 'Site Visit - Field Director';

interface SelectOption {
    uri: string;
    label: string;
}

function flattenOptions(nodes: ReferenceSelectTreeNode[]): SelectOption[] {
    return nodes.flatMap((node) => [
        { uri: node.data.uri, label: node.label },
        ...flattenOptions(node.children ?? []),
    ]);
}

function findOption(
    nodes: ReferenceSelectTreeNode[],
    label: string,
): ReferenceSelectTreeNode | null {
    for (const node of nodes) {
        if (node.label === label) return node;
        const found = findOption(node.children ?? [], label);
        if (found) return found;
    }
    return null;
}

const culturalAreaOptions = ref<SelectOption[]>([]);
const siteVisitFieldDirectorOption = ref<ReferenceSelectTreeNode | null>(null);

const emit = defineEmits(['update:step-is-valid']);

const { draftData, typedDraftData, isValid, updateValue } =
    useDraftStep<HcaPermitApplicationResourceAliasedData>(
        undefined,
        'personnel',
        emit,
    );

onMounted(async () => {
    const store = useReferenceSelectOptionsStore();
    const [areaNodes, roleNodes] = await Promise.all([
        store.fetchWidgetOptions('hca_permit_application', 'cultural_area'),
        store.fetchWidgetOptions(
            'hca_permit_application',
            'responsibility_role',
        ),
    ]);
    culturalAreaOptions.value = flattenOptions(areaNodes);
    siteVisitFieldDirectorOption.value = findOption(
        roleNodes,
        SITE_VISIT_FIELD_DIRECTOR_LABEL,
    );
});

const allTiles = computed(
    () =>
        typedDraftData.value?.personnel?.aliased_data
            ?.assessment_oversight_responsibility ?? [],
);

const culturalAreaTiles = computed(() =>
    allTiles.value.filter(
        (t) => !!t.aliased_data?.cultural_area?.node_value?.[0]?.uri,
    ),
);

const delegatedTiles = computed(() =>
    allTiles.value.filter(
        (t) => !t.aliased_data?.cultural_area?.node_value?.[0]?.uri,
    ),
);

const selectedAreaUris = computed(() =>
    culturalAreaTiles.value
        .map((t) => t.aliased_data?.cultural_area?.node_value?.[0]?.uri)
        .filter((uri): uri is string => !!uri),
);

function areaLabel(uri: string): string {
    return culturalAreaOptions.value.find((a) => a.uri === uri)?.label ?? uri;
}

function onSelectionChange(newUris: string[]) {
    const currentAll = allTiles.value;

    const newCulturalAreaTiles = newUris.map((uri) => {
        const existing = currentAll.find(
            (t) => t.aliased_data?.cultural_area?.node_value?.[0]?.uri === uri,
        );
        if (existing) return existing;

        const area = culturalAreaOptions.value.find((a) => a.uri === uri);
        const roleOption = siteVisitFieldDirectorOption.value;
        return {
            aliased_data: {
                cultural_area: {
                    node_value: [
                        {
                            uri,
                            labels: area
                                ? [{ value: area.label, language_id: 'en' }]
                                : [],
                        },
                    ],
                    display_value: area?.label ?? uri,
                },
                ...(roleOption && {
                    responsibility_role: {
                        node_value: roleOption.data.list_item_values
                            .filter((v) => v.valuetype_id === 'prefLabel')
                            .map((v) => ({
                                uri: roleOption.data.uri,
                                labels: [
                                    {
                                        value: v.value,
                                        language_id: v.language_id,
                                    },
                                ],
                            })),
                        display_value: roleOption.label,
                    },
                }),
            },
        };
    });

    const currentDelegated = currentAll.filter(
        (t) => !t.aliased_data?.cultural_area?.node_value?.[0]?.uri,
    );

    updateValue(
        [
            ...newCulturalAreaTiles,
            ...currentDelegated,
        ] as unknown as AliasedNodeData,
        'assessment_oversight_responsibility',
        'personnel',
    );
}

function addDelegatedRow() {
    updateValue(
        [...allTiles.value, { aliased_data: {} }] as unknown as AliasedNodeData,
        'assessment_oversight_responsibility',
        'personnel',
    );
}

function removeDelegatedRow(delegatedIndex: number) {
    const absoluteIndex = culturalAreaTiles.value.length + delegatedIndex;
    const all = allTiles.value;
    const updated = [
        ...all.slice(0, absoluteIndex),
        ...all.slice(absoluteIndex + 1),
    ];
    updateValue(
        updated as unknown as AliasedNodeData,
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
        <FieldSet legend="Site Visit - Field Director">
            <MultiSelect
                :model-value="selectedAreaUris"
                :options="culturalAreaOptions"
                option-label="label"
                option-value="uri"
                placeholder="Select cultural areas"
                display="chip"
                @update:model-value="onSelectionChange"
            />
            <div
                v-for="(tile, index) in culturalAreaTiles"
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
                </FieldSet>
            </div>
        </FieldSet>

        <FieldSet legend="Delegated Archaeologist">
            <div
                v-for="(_, delegatedIndex) in delegatedTiles"
                :key="delegatedIndex"
            >
                <GenericWidget
                    :mode="EDIT"
                    :aliased-node-data="
                        draftData?.personnel?.aliased_data
                            ?.assessment_oversight_responsibility?.[
                            culturalAreaTiles.length + delegatedIndex
                        ]?.aliased_data?.responsible_person
                    "
                    graph-slug="hca_permit_application"
                    node-alias="responsible_person"
                    @update:aliased-node-data="
                        updateValue($event, 'responsible_person', [
                            'personnel',
                            `assessment_oversight_responsibility[${culturalAreaTiles.length + delegatedIndex}]`,
                        ])
                    "
                />
                <button
                    type="button"
                    class="bc-remove-row"
                    @click="removeDelegatedRow(delegatedIndex)"
                >
                    Remove
                </button>
            </div>
            <button
                type="button"
                class="bc-add-row"
                @click="addDelegatedRow"
            >
                Add Delegated Archaeologist
            </button>
        </FieldSet>
    </Form>
</template>
