<script setup lang="ts">
import { ref, useTemplateRef, computed } from 'vue';
import type { Ref } from 'vue';
import { Form, type FormInstance } from '@primevue/forms';
import FieldSet from 'primevue/fieldset';
import Button from 'primevue/button';
import GenericWidget from '@/arches_component_lab/generics/GenericWidget/GenericWidget.vue';
import LabelledInput from '@/bcgov_arches_common/components/labelledinput/LabelledInput.vue';
import { EDIT, VIEW } from '@/arches_component_lab/widgets/constants.ts';
import { zDocumentSubmissionSubmissionPhotographsAliasedData } from '@/bcap/client/zod.gen.ts';
import { useDraftStep } from '@/bcap/composables/useDraftStep.ts';
import type { AliasedNodeData } from '@/arches_component_lab/types.ts';
import { useDraftStore } from '@/bcap/stores/draft.ts';
import { saveDraftFieldToBackend } from '@/bcap/apps/Permit/api.ts';

const emit = defineEmits(['update:step-is-valid']);
const draftStore = useDraftStore();

const { draftData, resolver, isValid } = useDraftStep(
    zDocumentSubmissionSubmissionPhotographsAliasedData,
    'submission_photographs',
    emit,
);

const getBlankPhotograph = () => {
    return {
        aliased_data: {
            submission_photographs: null,
            photograph_description: '',
            photograph_date: null,
            photograph_view: null,
            photographer: '',
        },
    };
};

const currentPhoto = ref(getBlankPhotograph());
const photoKey = ref<number>(0);
const addingNewImage = ref<boolean>(true);

// Ensure the draftData property is treated as an array
const photoList = computed(() => {
    if (!draftData.value?.submission_photographs) return [];
    return Array.isArray(draftData.value.submission_photographs)
        ? draftData.value.submission_photographs
        : [draftData.value.submission_photographs];
});

const photosCount = computed(() => photoList.value.length);

const hasUnsavedImage = computed(() => {
    const nodes = currentPhoto.value?.aliased_data?.submission_photographs;
    return nodes !== null && nodes !== undefined;
});

const photoForm: Ref<FormInstance | null> = useTemplateRef(
    'photoForm',
) as Ref<FormInstance | null>;

const addImageDisabled = computed(() => {
    if (photosCount.value >= 10) return true;
    if (!hasUnsavedImage.value) return true;

    const data = currentPhoto.value?.aliased_data;
    const hasView = !!data?.photograph_view;
    const hasDesc = !!data?.photograph_description;

    return !(hasView && hasDesc);
});

const nextImageKey = computed(() => photoList.value.length);

const addNewImage = () => {
    currentPhoto.value = getBlankPhotograph();
    addingNewImage.value = true;
    photoKey.value = nextImageKey.value;
};

const clearPendingImage = () => {
    currentPhoto.value = getBlankPhotograph();
    photoKey.value++;
};

// Generic manual update for the current drafted item
const updateCurrentValue = (
    newValue: AliasedNodeData,
    fieldName: keyof typeof currentPhoto.value.aliased_data,
) => {
    if (
        fieldName === 'photograph_date' &&
        newValue &&
        typeof newValue.node_value === 'string'
    ) {
        // correcting date format
        const val = newValue.node_value;
        if (/^\d{4}$/.test(val)) {
            newValue.node_value = `${val}-01-01T00:00:00Z`;
        } else if (/^\d{4}-\d{2}-\d{2}$/.test(val)) {
            newValue.node_value = `${val}T00:00:00Z`;
        }
    }

    currentPhoto.value.aliased_data[fieldName] = newValue as never;
};

const pendingFile = ref<File | null>(null);

const handleFileUpdate = (newValue: AliasedNodeData) => {
    console.log('INTERCEPTED FILE WIDGET UPDATE:', newValue);
    const nodeArray = newValue?.node_value as
        Array<Record<string, unknown>> | undefined;
    const fileObj = nodeArray?.[0]?.file;

    if (fileObj instanceof File) {
        pendingFile.value = fileObj;
        console.log('Successfully extracted raw File:', pendingFile.value.name);
    } else {
        pendingFile.value = null;
    }
    updateCurrentValue(newValue, 'submission_photographs');
};

type PhotographDraft = ReturnType<typeof getBlankPhotograph>;

const saveImage = async () => {
    const currentData = draftData.value.submission_photographs as unknown as
        PhotographDraft | PhotographDraft[] | null | undefined;

    const existingPhotos: PhotographDraft[] = Array.isArray(currentData)
        ? currentData
        : currentData
          ? [currentData]
          : [];

    const newPhotosArray = [...existingPhotos, currentPhoto.value];

    draftData.value.submission_photographs =
        newPhotosArray as unknown as typeof draftData.value.submission_photographs;

    if (draftStore.draftId) {
        if (pendingFile.value) {
            const formData = new FormData();
            formData.append('file', pendingFile.value);

            console.log(
                'Ready to execute manual file PATCH with:',
                formData.get('file'),
            );
        }

        const safeDraftData = JSON.parse(
            JSON.stringify(draftStore.draftData, (key, value) => {
                if (key === 'file' && value instanceof File) {
                    return undefined;
                }
                return value;
            }),
        );

        await saveDraftFieldToBackend(
            draftStore.draftId,
            draftStore.graphSlug,
            safeDraftData,
        );
    }

    // Reset UI
    pendingFile.value = null;
    currentPhoto.value = getBlankPhotograph();
    photoKey.value = nextImageKey.value;
    photoForm.value?.reset();

    emit('update:step-is-valid', isValid());
};

const deletePhoto = async (index: number) => {
    const currentData = draftData.value.submission_photographs as unknown as
        PhotographDraft | PhotographDraft[] | null | undefined;

    if (Array.isArray(currentData)) {
        currentData.splice(index, 1);

        draftData.value.submission_photographs =
            currentData as unknown as typeof draftData.value.submission_photographs;

        if (draftStore.draftId) {
            await saveDraftFieldToBackend(
                draftStore.draftId,
                draftStore.graphSlug,
                draftStore.draftData,
            );
        }

        emit('update:step-is-valid', isValid());
    }
};

const setCurrentPhoto = (index: number) => {
    currentPhoto.value = photoList.value[index];
    photoKey.value = index;
    addingNewImage.value = false;
};

const save = async () => {
    return true;
};

defineExpose({ isValid, save });
</script>

<template>
    <Form
        ref="photoForm"
        v-slot="$form"
        name="photoForm"
        :validateOnBlur="true"
        :resolver="resolver"
    >
        <FieldSet legend="Submission Photographs">
            <div class="flex flex-row flex-nowrap">
                <div class="uploader-container">
                    <div
                        v-if="
                            photosCount >= 10 &&
                            !hasUnsavedImage &&
                            addingNewImage
                        "
                        class="max-limit-message"
                    >
                        <i class="fa fa-ban limit-icon"></i>
                        <div>Maximum of 10 images reached.</div>
                        <div class="limit-subtext">
                            Please delete an image to add more.
                        </div>
                    </div>

                    <!-- INTERCEPTED FILE WIDGET -->
                    <GenericWidget
                        v-else-if="!hasUnsavedImage && addingNewImage"
                        :key="photoKey"
                        graph-slug="document_submission"
                        node-alias="submission_photographs"
                        :should-show-label="false"
                        :mode="EDIT"
                        :aliased-node-data="
                            currentPhoto?.aliased_data?.submission_photographs
                        "
                        @update:value="handleFileUpdate"
                    ></GenericWidget>

                    <div
                        v-else
                        class="pending-image-preview"
                    >
                        <GenericWidget
                            :key="`view-${photoKey}`"
                            graph-slug="document_submission"
                            node-alias="submission_photographs"
                            :should-show-label="false"
                            :mode="VIEW"
                            :aliased-node-data="
                                currentPhoto?.aliased_data
                                    ?.submission_photographs
                            "
                        ></GenericWidget>

                        <Button
                            v-if="addingNewImage"
                            label="Remove / Change Image"
                            icon="fa fa-times"
                            @click="clearPendingImage"
                        />
                    </div>
                </div>

                <div class="placeholders">
                    <div>
                        <Button
                            v-if="!addingNewImage && photosCount < 10"
                            label="+ Add"
                            class="inline-block"
                            :aria-disabled="addImageDisabled"
                            :disabled="addImageDisabled"
                            @click="addNewImage"
                        ></Button>
                        <Button
                            v-if="addingNewImage && photosCount < 10"
                            class="inline-block"
                            :aria-disabled="addImageDisabled"
                            :disabled="addImageDisabled"
                            tooltip="Save the new image before adding another"
                            @click="saveImage"
                        >
                            <i class="fa fa-save mr-2"></i>
                            Save Image
                        </Button>
                    </div>

                    <!-- Thumbnails / Gallery -->
                    <div class="flex flex-row image-placeholders">
                        <div
                            v-for="(photo, index) in photoList"
                            :key="index"
                            :data-selected="index === photoKey"
                            class="image-placeholder"
                            @click="setCurrentPhoto(index)"
                        >
                            <div
                                class="fa fa-remove image-icons image-delete-icon"
                                tooltip="Remove Image"
                                @click.stop="deletePhoto(index)"
                            ></div>
                            <GenericWidget
                                graph-slug="document_submission"
                                :mode="VIEW"
                                :should-show-label="false"
                                node-alias="submission_photographs"
                                :aliased-node-data="
                                    photo.aliased_data.submission_photographs
                                "
                            />
                        </div>
                    </div>
                </div>
            </div>

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
                :error-message="$form.photographDescription?.error?.message"
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
                        :error-message="$form.photographer?.error?.message"
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
.flex-column {
    flex-direction: column;
}
.flex-row {
    flex-direction: row;
    align-items: start;
}
.flex-nowrap {
    flex-wrap: nowrap;
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

.uploader-container {
    width: 300px;
    min-height: 200px;
}

.max-limit-message {
    width: 100%;
    height: 100%;
    min-height: 200px;
    background: #f8f9fa;
    border: 2px dashed #dee2e6;
    border-radius: 6px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: #495057;
    font-weight: 600;
}

.limit-icon {
    font-size: 2rem;
    margin-bottom: 0.5rem;
    color: #aaa;
}

.limit-subtext {
    font-size: 0.8em;
    color: #666;
}

.pending-image-preview {
    border: 1px solid #ddd;
    padding: 10px;
    border-radius: 4px;
    text-align: center;
}

.image-placeholders {
    flex-flow: wrap;
    gap: 0.25rem;
}

.image-placeholder {
    max-width: 125px;
    min-width: 125px;
    max-height: 125px;
    position: relative;
    overflow: hidden;
    cursor: pointer;
}

.image-icons {
    position: absolute;
    right: 0.5rem;
    cursor: pointer;
    width: 1rem;
    height: 1rem;
    z-index: 1000;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2px;
    border-radius: 3px;
}

.image-delete-icon {
    top: 0.5rem;
    color: red;
}
</style>
<style>
.image-placeholder[data-selected='false'] {
    opacity: 0.7;
}
</style>
