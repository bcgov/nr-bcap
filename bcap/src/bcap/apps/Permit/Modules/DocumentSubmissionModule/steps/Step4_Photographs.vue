<script setup lang="ts">
import { ref, useTemplateRef, computed, watch } from 'vue';
import type { Ref } from 'vue';
import { Form, type FormInstance } from '@primevue/forms';
import FieldSet from 'primevue/fieldset';
import GenericWidget from '@/arches_component_lab/generics/GenericWidget/GenericWidget.vue';
import LabelledInput from '@/bcgov_arches_common/components/labelledinput/LabelledInput.vue';
import { EDIT } from '@/arches_component_lab/widgets/constants.ts';
import type { AliasedNodeData } from '@/arches_component_lab/types.ts';
import { useDraftStore } from '@/bcap/stores/draft.ts';
import { saveDraftFieldToBackend } from '@/bcap/apps/Permit/api.ts';
import MultiFileUploader from '@/bcgov_arches_common/components/fileUpload/MultiFileUploader.vue';

import type {
    DocumentSubmissionSubmissionPhotographsTile,
    DocumentSubmissionSubmissionPhotographsAliasedData,
    FileListAliasedNodeData,
    StringAliasedNodeData,
} from '@/bcap/client/types.gen.ts';

const emit = defineEmits(['update:step-is-valid']);
const draftStore = useDraftStore();
const draftData = computed(() => draftStore.draftData);

const getBlankPhotograph = (): DocumentSubmissionSubmissionPhotographsTile => ({
    aliased_data: {
        submission_photographs: null,
        photograph_description: null,
        photograph_date: null,
        photograph_view: null,
        photographer: null,
    },
});

const currentPhoto =
    ref<DocumentSubmissionSubmissionPhotographsTile>(getBlankPhotograph());
const photoKey = ref<number>(0);
const addingNewImage = ref<boolean>(true);
const photoForm: Ref<FormInstance | null> = useTemplateRef(
    'photoForm',
) as Ref<FormInstance | null>;

const photoList = computed(() => {
    if (!draftData.value?.submission_photographs) return [];
    return Array.isArray(draftData.value.submission_photographs)
        ? draftData.value.submission_photographs
        : [draftData.value.submission_photographs];
});

const addImageDisabled = computed(() => {
    const fileNode = currentPhoto.value.aliased_data?.submission_photographs as
        FileListAliasedNodeData | null | undefined;
    const isUnsaved =
        !!fileNode &&
        Array.isArray(fileNode.node_value) &&
        fileNode.node_value.length > 0;

    if (!isUnsaved) return true;

    const viewNode = currentPhoto.value.aliased_data?.photograph_view as
        StringAliasedNodeData | undefined;
    const vVal = viewNode?.node_value;
    const hasView = !!(
        viewNode?.display_value ||
        vVal?.en?.value ||
        (typeof vVal === 'string' && (vVal as string).trim() !== '')
    );

    const descNode = currentPhoto.value.aliased_data?.photograph_description as
        StringAliasedNodeData | undefined;
    const dVal = descNode?.node_value;
    const hasDesc = !!(
        descNode?.display_value ||
        dVal?.en?.value ||
        (typeof dVal === 'string' && (dVal as string).trim() !== '')
    );

    return !(hasView && hasDesc);
});

const updateCurrentValue = (
    newValue: AliasedNodeData,
    fieldName: keyof DocumentSubmissionSubmissionPhotographsAliasedData,
) => {
    if (
        fieldName === 'photograph_date' &&
        newValue &&
        typeof newValue.node_value === 'string'
    ) {
        const val = newValue.node_value;
        if (/^\d{4}$/.test(val)) newValue.node_value = `${val}-01-01T00:00:00Z`;
        else if (/^\d{4}-\d{2}-\d{2}$/.test(val))
            newValue.node_value = `${val}T00:00:00Z`;
    }

    if (!currentPhoto.value.aliased_data) {
        currentPhoto.value.aliased_data = {};
    }

    // @ts-expect-error - Dynamic assignment mapping generic Arches nodes
    currentPhoto.value.aliased_data[fieldName] = newValue;
};

const addNewImage = () => {
    currentPhoto.value = getBlankPhotograph();
    addingNewImage.value = true;
    photoKey.value = photoList.value.length;
};

const clearPendingImage = () => {
    currentPhoto.value = getBlankPhotograph();
    photoKey.value++;
};

const customIsValid = () => {
    const fileNode = currentPhoto.value.aliased_data?.submission_photographs as
        FileListAliasedNodeData | null | undefined;
    const isUnsaved =
        !!fileNode &&
        Array.isArray(fileNode.node_value) &&
        fileNode.node_value.length > 0;

    if (photoList.value.length === 0 && !isUnsaved) return false;

    for (const photo of photoList.value) {
        const viewNode = photo.aliased_data?.photograph_view as
            StringAliasedNodeData | undefined;
        const vVal = viewNode?.node_value;
        const hasView = !!(
            viewNode?.display_value ||
            vVal?.en?.value ||
            (typeof vVal === 'string' && (vVal as string).trim() !== '')
        );

        const descNode = photo.aliased_data?.photograph_description as
            StringAliasedNodeData | undefined;
        const dVal = descNode?.node_value;
        const hasDesc = !!(
            descNode?.display_value ||
            dVal?.en?.value ||
            (typeof dVal === 'string' && (dVal as string).trim() !== '')
        );

        if (!hasView || !hasDesc) return false;
    }

    if (addingNewImage.value && isUnsaved && addImageDisabled.value)
        return false;

    return true;
};

watch(
    () => [photoList.value, currentPhoto.value, addingNewImage.value],
    () => emit('update:step-is-valid', customIsValid()),
    { deep: true, immediate: true },
);

const saveImage = async () => {
    const currentData = draftData.value.submission_photographs;
    const existingPhotos: DocumentSubmissionSubmissionPhotographsTile[] =
        Array.isArray(currentData)
            ? currentData
            : currentData
              ? [currentData as DocumentSubmissionSubmissionPhotographsTile]
              : [];

    draftData.value.submission_photographs = [
        ...existingPhotos,
        currentPhoto.value,
    ] as typeof draftData.value.submission_photographs;

    if (draftStore.draftId) {
        const safeDraftData = JSON.parse(
            JSON.stringify(draftStore.draftData, (key, value) =>
                key === 'file' && value instanceof File ? undefined : value,
            ),
        );
        await saveDraftFieldToBackend(
            draftStore.draftId,
            draftStore.graphSlug,
            safeDraftData,
        );
    }

    currentPhoto.value = getBlankPhotograph();
    photoKey.value = photoList.value.length;
    photoForm.value?.reset();
    emit('update:step-is-valid', customIsValid());
};

const deletePhoto = async (index: number) => {
    const currentData = draftData.value.submission_photographs;
    if (Array.isArray(currentData)) {
        currentData.splice(index, 1);
        draftData.value.submission_photographs = currentData;

        if (draftStore.draftId) {
            await saveDraftFieldToBackend(
                draftStore.draftId,
                draftStore.graphSlug,
                draftStore.draftData,
            );
        }
        emit('update:step-is-valid', customIsValid());
    }
};

const setCurrentPhoto = (index: number) => {
    currentPhoto.value = photoList.value[index];
    photoKey.value = index;
    addingNewImage.value = false;
};

defineExpose({ isValid: customIsValid, save: async () => true });
</script>

<template>
    <Form
        ref="photoForm"
        name="photoForm"
        :validateOnBlur="true"
    >
        <FieldSet legend="Submission Photographs">
            <MultiFileUploader
                :adding-new="addingNewImage"
                :disable-add-or-save="addImageDisabled"
                graph-slug="document_submission"
                node-alias="submission_photographs"
                :current-node-data="
                    currentPhoto?.aliased_data?.submission_photographs
                "
                :items="photoList"
                :selected-index="photoKey"
                item-type-label="Image"
                icon-class="fa-image"
                @file-updated="
                    updateCurrentValue($event, 'submission_photographs')
                "
                @clear-pending="clearPendingImage"
                @add-new="addNewImage"
                @save-item="saveImage"
                @delete-item="deletePhoto"
                @select-item="setCurrentPhoto"
            />

            <!-- Metadata Form -->
            <div class="flex flex-row mt-4">
                <div class="flex-grow">
                    <LabelledInput
                        label="Photograph View"
                        hint="Select the view that best describes the image"
                        input-name="photographView"
                        :required="true"
                    >
                        <div class="p-inputtext-fluid">
                            <GenericWidget
                                :key="photoKey"
                                graph-slug="document_submission"
                                node-alias="photograph_view"
                                :mode="EDIT"
                                :aliased-node-data="
                                    currentPhoto?.aliased_data?.photograph_view
                                "
                                :should-show-label="false"
                                placeholder="Select an Image View"
                                @update:value="
                                    updateCurrentValue(
                                        $event,
                                        'photograph_view',
                                    )
                                "
                            />
                        </div>
                    </LabelledInput>
                </div>
            </div>

            <LabelledInput
                label="Photograph Description"
                hint="Summarize the image content. Include additional information that does not fit fields above"
                input-name="photographDescription"
                :required="true"
            >
                <div class="p-inputtext-fluid">
                    <GenericWidget
                        :key="photoKey"
                        :mode="EDIT"
                        :should-show-label="false"
                        :aliasedNodeData="
                            currentPhoto?.aliased_data?.photograph_description
                        "
                        graph-slug="document_submission"
                        node-alias="photograph_description"
                        placeholder="E.g. Front view of the excavation site..."
                        @update:value="
                            updateCurrentValue($event, 'photograph_description')
                        "
                    />
                </div>
            </LabelledInput>

            <div class="flex flex-row gap-4">
                <div class="flex-grow">
                    <LabelledInput
                        label="Photograph Date"
                        hint="Date the image was created"
                        input-name="photographDate"
                    >
                        <div class="p-inputtext-fluid">
                            <GenericWidget
                                :key="photoKey"
                                :mode="EDIT"
                                :should-show-label="false"
                                :aliasedNodeData="
                                    currentPhoto?.aliased_data?.photograph_date
                                "
                                graph-slug="document_submission"
                                node-alias="photograph_date"
                                group-direction="column"
                                @update:value="
                                    updateCurrentValue(
                                        $event,
                                        'photograph_date',
                                    )
                                "
                            />
                        </div>
                    </LabelledInput>
                </div>

                <div class="flex-grow">
                    <LabelledInput
                        label="Photographer"
                        hint="Enter the name of the photographer"
                        input-name="photographer"
                    >
                        <div class="p-inputtext-fluid">
                            <GenericWidget
                                :key="photoKey"
                                :mode="EDIT"
                                :should-show-label="false"
                                :aliasedNodeData="
                                    currentPhoto?.aliased_data?.photographer
                                "
                                graph-slug="document_submission"
                                node-alias="photographer"
                                placeholder="First Name Last Name"
                                @update:value="
                                    updateCurrentValue($event, 'photographer')
                                "
                            />
                        </div>
                    </LabelledInput>
                </div>
            </div>
        </FieldSet>
    </Form>
    <br />
    <br />
</template>

<style scoped>
:deep(label) {
    font-weight: bold;
}

.flex {
    display: flex;
    gap: 1.5rem;
}
.flex-row {
    flex-direction: row;
    align-items: start;
}
.flex-grow {
    flex-grow: 1;
}
.gap-4 {
    gap: 1rem;
}
.mt-4 {
    margin-top: 1rem;
}
</style>
