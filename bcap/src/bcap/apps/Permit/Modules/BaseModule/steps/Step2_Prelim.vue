<script setup lang="ts">
import { inject, type Ref } from 'vue';
import GenericWidget from '@/arches_component_lab/generics/GenericWidget/GenericWidget.vue';
import { EDIT } from '@/arches_component_lab/widgets/constants.ts';
import FieldSet from 'primevue/fieldset';
import type { AliasedNodeData } from '@/arches_component_lab/types.ts';
import { saveFieldToBackend } from '@/bcap/util.ts';
import type { ArchesDraftData } from '@/bcap/types.ts';

const draftId = inject<Ref<string | null>>('draftId');
const draftData = inject<Ref<ArchesDraftData>>('draftData');
const graphSlug = 'permit_application';

const isValid = () => {
    return true;
};

let timeoutId: ReturnType<typeof setTimeout>;

const updateValue = (
    newValue: AliasedNodeData,
    attribute_name: string,
    node_group_alias: string | string[],
) => {
    if (!draftData?.value) return;

    const groups = Array.isArray(node_group_alias)
        ? node_group_alias
        : [node_group_alias];

    let currentLevel = draftData.value as Record<string, unknown>;

    groups.forEach((group, index) => {
        const match = group.match(/^(.+)\[(\d+)\]$/);

        if (match) {
            const name = match[1];
            const arrIndex = parseInt(match[2], 10);
            if (!currentLevel[name]) currentLevel[name] = [];
            const arr = currentLevel[name] as Record<string, unknown>[];
            if (!arr[arrIndex]) arr[arrIndex] = { aliased_data: {} };
            if (index === groups.length - 1) {
                const target = arr[arrIndex].aliased_data as Record<
                    string,
                    unknown
                >;
                target[attribute_name] = newValue;
            } else {
                currentLevel = arr[arrIndex].aliased_data as Record<
                    string,
                    unknown
                >;
            }
        } else {
            if (!currentLevel[group])
                currentLevel[group] = { aliased_data: {} };
            const node = currentLevel[group] as {
                aliased_data: Record<string, unknown>;
            };

            if (index === groups.length - 1) {
                node.aliased_data[attribute_name] = newValue;
            } else {
                currentLevel = node.aliased_data;
            }
        }
    });

    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => {
        if (draftId?.value) {
            saveFieldToBackend(draftId.value, graphSlug, draftData.value);
        }
    }, 1000);
};

defineExpose({ isValid });
</script>

<template>
    <FieldSet legend="">
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="
                draftData?.application_identification?.aliased_data
                    ?.is_replacement
            "
            graph-slug="permit_application"
            node-alias="is_replacement"
            @update:value="
                updateValue(
                    $event,
                    'is_replacement',
                    'application_identification',
                )
            "
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="
                draftData?.application_identification?.aliased_data
                    ?.project_name
            "
            graph-slug="permit_application"
            node-alias="project_name"
            @update:value="
                updateValue(
                    $event,
                    'project_name',
                    'application_identification',
                )
            "
        />
        <div class="row">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.application_identification?.aliased_data
                        ?.application_id
                "
                graph-slug="permit_application"
                node-alias="application_id"
                @update:value="
                    updateValue(
                        $event,
                        'application_id',
                        'application_identification',
                    )
                "
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.proposed_project?.aliased_data?.project_type
                "
                graph-slug="permit_application"
                node-alias="project_type"
                @update:value="
                    updateValue($event, 'project_type', 'proposed_project')
                "
            />
        </div>
        <GenericWidget
            class="description-box"
            :mode="EDIT"
            :aliased-node-data="
                draftData?.proposed_project?.aliased_data?.project_description
            "
            graph-slug="permit_application"
            node-alias="project_description"
            @update:value="
                updateValue($event, 'project_description', 'proposed_project')
            "
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="
                draftData?.proposed_project?.aliased_data?.scope_of_work
            "
            graph-slug="permit_application"
            node-alias="scope_of_work"
            @update:value="
                updateValue($event, 'scope_of_work', 'proposed_project')
            "
        />
    </FieldSet>
    <br />
</template>

<style scoped>
.row {
    display: flex;
    gap: 1rem;
    width: 100%;
}
.row > * {
    flex: 1;
}
</style>
