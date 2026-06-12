<script setup lang="ts">
import { inject, type Ref } from 'vue';
import GenericWidget from '@/arches_component_lab/generics/GenericWidget/GenericWidget.vue';
import { EDIT } from '@/arches_component_lab/widgets/constants.ts';
import FieldSet from 'primevue/fieldset';
import type { AliasedNodeData } from '@/arches_component_lab/types.ts';
import { updateDraftValue } from '@/bcap/util.ts';
import type { ArchesDraftData } from '@/bcap/types.ts';

const draftId = inject<Ref<string | null>>('draftId');
const draftData = inject<Ref<ArchesDraftData>>('draftData');
const graphSlug = 'permit_application';

const isValid = () => {
    return true;
};

const updateValue = (
    newValue: AliasedNodeData,
    attribute_name: string,
    node_group_alias: string | string[],
) => {
    updateDraftValue(
        draftData?.value,
        draftId?.value,
        graphSlug,
        newValue,
        attribute_name,
        node_group_alias,
    );
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
