<script setup lang="ts">
import { inject, type Ref } from 'vue';
import GenericWidget from '@/arches_component_lab/generics/GenericWidget/GenericWidget.vue';
import { EDIT } from '@/arches_component_lab/widgets/constants.ts';
import FieldSet from 'primevue/fieldset';
import type { AliasedNodeData } from '@/arches_component_lab/types.ts';

const draftId = inject<Ref<string | null>>('draftId');
const draftData = inject<Ref<Record<string, unknown>>>('draftData');
const graphSlug = 'permit_application';

const isValid = () => {
    return true;
};

let timeoutId: ReturnType<typeof setTimeout>;

const getCsrfToken = () => {
    return (
        document.cookie
            .split('; ')
            .find((row) => row.startsWith('csrftoken='))
            ?.split('=')[1] || ''
    );
};

const saveFieldToBackend = async (
    attribute_name: string,
    newValue: AliasedNodeData,
) => {
    if (!draftId?.value) return;

    try {
        const patchUrl = `/bcap/api/resource_draft/${graphSlug}/${draftId.value}`;

        const response = await fetch(patchUrl, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
            },
            body: JSON.stringify({
                data: {
                    [attribute_name]: newValue,
                },
            }),
        });

        if (!response.ok) {
            throw new Error(`Server returned ${response.status}`);
        }

        console.log(`Successfully auto-saved: ${attribute_name}`);
    } catch (error) {
        console.error(`Failed to auto-save ${attribute_name}:`, error);
    }
};

const updateValue = (newValue: AliasedNodeData, attribute_name: string) => {
    // update the local Vue state so the Review page sees it
    if (draftData?.value) {
        draftData.value[attribute_name] = newValue;
    }

    //debounce to save to the backend
    clearTimeout(timeoutId);

    timeoutId = setTimeout(() => {
        saveFieldToBackend(attribute_name, newValue);
    }, 1000);
};

defineExpose({ isValid });
</script>

<template>
    <FieldSet legend="">
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="draftData?.is_replacement"
            graph-slug="permit_application"
            node-alias="is_replacement"
            @update:value="updateValue($event, 'is_replacement')"
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="draftData?.project_name"
            graph-slug="permit_application"
            node-alias="project_name"
            @update:value="updateValue($event, 'project_name')"
        />
        <div class="row">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="draftData?.application_id"
                graph-slug="permit_application"
                node-alias="application_id"
                @update:value="updateValue($event, 'application_id')"
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="draftData?.project_type"
                graph-slug="permit_application"
                node-alias="project_type"
                @update:value="updateValue($event, 'project_type')"
            />
        </div>
        <GenericWidget
            class="description-box"
            :mode="EDIT"
            :aliased-node-data="draftData?.project_description"
            graph-slug="permit_application"
            node-alias="project_description"
            @update:value="updateValue($event, 'project_description')"
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="draftData?.scope_of_work"
            graph-slug="permit_application"
            node-alias="scope_of_work"
            @update:value="updateValue($event, 'scope_of_work')"
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
