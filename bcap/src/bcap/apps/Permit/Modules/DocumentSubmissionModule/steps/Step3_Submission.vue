<script setup lang="ts">
import { ref, computed, watch, inject } from 'vue';
import type { Ref } from 'vue';
import { Form } from '@primevue/forms';
import FieldSet from 'primevue/fieldset';
import GenericWidget from '@/arches_component_lab/generics/GenericWidget/GenericWidget.vue';
import LabelledInput from '@/bcgov_arches_common/components/labelledinput/LabelledInput.vue';
import { EDIT } from '@/arches_component_lab/widgets/constants.ts';
import { useDraftStore } from '@/bcap/stores/draft.ts';
import { saveDraftFieldToBackend } from '@/bcap/apps/Permit/api.ts';
import MultiFileUploader from '@/bcgov_arches_common/components/fileUpload/MultiFileUploader.vue';

import type {
    AliasedNodeData,
    CardXNodeXWidgetData,
} from '@/arches_component_lab/types.ts';
import type {
    DocumentSubmissionReportSubmissionAliasedData,
    FileListAliasedNodeData,
} from '@/bcap/client/types.gen.ts';

const emit = defineEmits(['update:step-is-valid']);
const draftStore = useDraftStore();
const draftData = computed(() => draftStore.draftData);

const cardComponents = inject<Ref<CardXNodeXWidgetData[]>>('cardComponents');

const blueprints = computed(() => {
    const comps = cardComponents?.value || [];
    return comps.reduce(
        (acc, curr) => {
            acc[curr.node.alias] = curr;
            return acc;
        },
        {} as Record<string, CardXNodeXWidgetData>,
    );
});

if (!draftData.value.report_submission) {
    draftData.value.report_submission = { aliased_data: {} };
}

interface SingleFileWrapper {
    aliased_data: {
        report_file: FileListAliasedNodeData | null;
    };
}

const getBlankFileNode = (): SingleFileWrapper => ({
    aliased_data: { report_file: null },
});
const currentFile = ref<SingleFileWrapper>(getBlankFileNode());
const docKey = ref<number>(0);
const addingNewDoc = ref<boolean>(true);

const docList = computed<SingleFileWrapper[]>(() => {
    const aliasedData = draftData.value.report_submission?.aliased_data as
        DocumentSubmissionReportSubmissionAliasedData | undefined;
    const files = aliasedData?.report_file?.node_value;
    if (!Array.isArray(files)) return [];
    return files.map((f) => ({
        aliased_data: { report_file: { node_value: [f] } },
    }));
});

const hasUnsavedFile = computed(() => {
    const fileNode = currentFile.value?.aliased_data?.report_file;
    return (
        !!fileNode &&
        Array.isArray(fileNode.node_value) &&
        fileNode.node_value.length > 0
    );
});

const addDocDisabled = computed(() => {
    return !hasUnsavedFile.value;
});

const customIsValid = () => {
    if (docList.value.length === 0) return false;

    const reportData = draftData.value.report_submission?.aliased_data as
        DocumentSubmissionReportSubmissionAliasedData | undefined;
    if (!reportData) return false;

    const titleNode = reportData.report_title;
    const tVal = titleNode?.node_value;

    const hasTitle = !!(titleNode?.display_value || tVal?.en?.value?.trim());

    const consultantNode = reportData.archaeological_consultant;
    const hasConsultant = !!(
        consultantNode?.display_value ||
        (Array.isArray(consultantNode?.node_value) &&
            consultantNode.node_value.length > 0)
    );

    return hasTitle && hasConsultant;
};

watch(
    () => [
        docList.value,
        currentFile.value,
        addingNewDoc.value,
        draftData.value.report_submission,
    ],
    () => emit('update:step-is-valid', customIsValid()),
    { deep: true, immediate: true },
);

const updateMetadata = async (
    newValue: AliasedNodeData,
    fieldName: keyof DocumentSubmissionReportSubmissionAliasedData,
) => {
    if (!draftData.value.report_submission) {
        draftData.value.report_submission = { aliased_data: {} };
    }

    const aliasedData = draftData.value.report_submission
        .aliased_data as DocumentSubmissionReportSubmissionAliasedData;
    // @ts-expect-error - Dynamic assignment on typed object
    aliasedData[fieldName] = newValue;

    emit('update:step-is-valid', customIsValid());

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
};

const handleFileUpdated = (newValue: unknown) => {
    currentFile.value.aliased_data.report_file =
        newValue as FileListAliasedNodeData;
    emit('update:step-is-valid', customIsValid());
};

const saveDoc = async () => {
    const fileNode = currentFile.value.aliased_data.report_file;
    const newFileVals = fileNode?.node_value;
    if (!Array.isArray(newFileVals) || newFileVals.length === 0) return;

    if (!draftData.value.report_submission) {
        draftData.value.report_submission = { aliased_data: {} };
    }

    const reportData = draftData.value.report_submission
        .aliased_data as DocumentSubmissionReportSubmissionAliasedData;

    if (!reportData.report_file) reportData.report_file = { node_value: [] };
    if (!Array.isArray(reportData.report_file.node_value)) {
        reportData.report_file.node_value = [];
    }

    reportData.report_file.node_value.push(...newFileVals);

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

    currentFile.value = getBlankFileNode();
    docKey.value = docList.value.length;
    emit('update:step-is-valid', customIsValid());
};

const deleteDoc = async (index: number) => {
    const aliasedData = draftData.value.report_submission?.aliased_data as
        DocumentSubmissionReportSubmissionAliasedData | undefined;
    const fileArray = aliasedData?.report_file?.node_value;

    if (Array.isArray(fileArray)) {
        fileArray.splice(index, 1);
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
        emit('update:step-is-valid', customIsValid());
    }
};

const addNewDoc = () => {
    currentFile.value = getBlankFileNode();
    addingNewDoc.value = true;
    docKey.value = docList.value.length;
};

const clearPendingDoc = () => {
    currentFile.value = getBlankFileNode();
    docKey.value++;
};

const setCurrentDoc = (index: number) => {
    currentFile.value = docList.value[index];
    docKey.value = index;
    addingNewDoc.value = false;
};

defineExpose({ isValid: customIsValid, save: async () => true });
</script>

<template>
    <Form
        name="docForm"
        :validateOnBlur="true"
    >
        <FieldSet legend="Document Submissions">
            <MultiFileUploader
                :adding-new="addingNewDoc"
                :disable-add-or-save="addDocDisabled"
                graph-slug="document_submission"
                node-alias="report_file"
                :current-node-data="currentFile?.aliased_data?.report_file"
                :items="docList"
                :selected-index="docKey"
                item-type-label="Document"
                icon-class="fa-file"
                @file-updated="handleFileUpdated"
                @clear-pending="clearPendingDoc"
                @add-new="addNewDoc"
                @save-item="saveDoc"
                @delete-item="deleteDoc"
                @select-item="setCurrentDoc"
            />

            <!-- Metadata Fields that apply to all uploaded files -->
            <div class="flex flex-column mt-4 gap-4">
                <LabelledInput
                    label="Report Title"
                    input-name="reportTitle"
                    :required="true"
                >
                    <GenericWidget
                        :card-x-node-x-widget-data="blueprints['report_title']"
                        :mode="EDIT"
                        :should-show-label="false"
                        :aliasedNodeData="
                            draftData?.report_submission?.aliased_data
                                ?.report_title
                        "
                        graph-slug="document_submission"
                        node-alias="report_title"
                        @update:value="updateMetadata($event, 'report_title')"
                    />
                </LabelledInput>

                <LabelledInput
                    label="Archaeological Consultant"
                    input-name="archConsultant"
                    :required="true"
                >
                    <GenericWidget
                        :card-x-node-x-widget-data="
                            blueprints['archaeological_consultant']
                        "
                        :mode="EDIT"
                        :should-show-label="false"
                        :aliasedNodeData="
                            draftData?.report_submission?.aliased_data
                                ?.archaeological_consultant
                        "
                        graph-slug="document_submission"
                        node-alias="archaeological_consultant"
                        @update:value="
                            updateMetadata($event, 'archaeological_consultant')
                        "
                    />
                </LabelledInput>

                <LabelledInput
                    label="Consultant Report Number"
                    input-name="reportNumber"
                >
                    <GenericWidget
                        :card-x-node-x-widget-data="
                            blueprints['consultant_report_number']
                        "
                        :mode="EDIT"
                        :should-show-label="false"
                        :aliasedNodeData="
                            draftData?.report_submission?.aliased_data
                                ?.consultant_report_number
                        "
                        graph-slug="document_submission"
                        node-alias="consultant_report_number"
                        @update:value="
                            updateMetadata($event, 'consultant_report_number')
                        "
                    />
                </LabelledInput>

                <LabelledInput
                    label="Archaeological Company"
                    input-name="archCompany"
                >
                    <GenericWidget
                        :card-x-node-x-widget-data="
                            blueprints['archaological_company']
                        "
                        :mode="EDIT"
                        :should-show-label="false"
                        :aliasedNodeData="
                            draftData?.report_submission?.aliased_data
                                ?.archaological_company
                        "
                        graph-slug="document_submission"
                        node-alias="archaological_company"
                        @update:value="
                            updateMetadata($event, 'archaological_company')
                        "
                    />
                </LabelledInput>

                <LabelledInput
                    label="Report Recommendations"
                    input-name="reportRecs"
                >
                    <GenericWidget
                        :card-x-node-x-widget-data="
                            blueprints['report_recommendations']
                        "
                        :mode="EDIT"
                        :should-show-label="false"
                        :aliasedNodeData="
                            draftData?.report_submission?.aliased_data
                                ?.report_recommendations
                        "
                        graph-slug="document_submission"
                        node-alias="report_recommendations"
                        @update:value="
                            updateMetadata($event, 'report_recommendations')
                        "
                    />
                </LabelledInput>
            </div>
        </FieldSet>
    </Form>
</template>

<style scoped>
:deep(label) {
    font-weight: bold;
}

.flex {
    display: flex;
}
.flex-column {
    flex-direction: column;
}
.gap-4 {
    gap: 1rem;
}
.mt-4 {
    margin-top: 1rem;
}
</style>
