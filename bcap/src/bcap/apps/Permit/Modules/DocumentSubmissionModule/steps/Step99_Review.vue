<script setup lang="ts">
import Step99_Review from '@/bcap/apps/Permit/Modules/Step99_Review.vue';
import GenericReviewSummary from '@/bcap/apps/Permit/Modules/ReviewSummary.vue';
import GenericWidget from '@/arches_component_lab/generics/GenericWidget/GenericWidget.vue';
import FieldSet from 'primevue/fieldset';
import { VIEW } from '@/arches_component_lab/widgets/constants.ts';
import type { ArchesDraftData } from '@/bcap/types.ts';

defineProps<{
    isSubmittedView?: boolean;
    resourceData?: ArchesDraftData | null;
}>();

const isValid = () => true;
defineExpose({ isValid });

type NodeData = Record<string, unknown>;

interface PhotographNode {
    aliased_data?: {
        submission_photographs?: unknown;
        photograph_description?: unknown;
        photograph_view?: unknown;
        photographer?: unknown;
        photograph_date?: unknown;
    };
}

interface ReportNode {
    aliased_data?: {
        report_file?: unknown;
        report_title?: unknown;
        archaeological_consultant?: unknown;
        consultant_report_number?: unknown;
        archaological_company?: unknown;
        report_recommendations?: unknown;
    };
}

const getFilteredFields = (fields: unknown) => {
    if (!Array.isArray(fields)) return [];

    return fields.filter((f) => {
        const alias = f.alias || f.nodeAlias || f.node?.alias || f.node_alias;
        return (
            alias !== 'submission_photographs' && alias !== 'report_submission'
        );
    });
};

const getPhotos = (rawData: unknown): PhotographNode[] => {
    if (!rawData) return [];
    const data = rawData as NodeData;
    let photos: unknown = null;

    const processNode = (
        Array.isArray(data.document_submission_process)
            ? data.document_submission_process[0]
            : data.document_submission_process
    ) as NodeData | undefined;
    const nestedAliasedData = processNode?.aliased_data as NodeData | undefined;

    if (nestedAliasedData?.submission_photographs)
        photos = nestedAliasedData.submission_photographs;
    else if (data.submission_photographs) photos = data.submission_photographs;

    if (!photos) return [];
    return Array.isArray(photos)
        ? (photos as PhotographNode[])
        : [photos as PhotographNode];
};

const getReport = (rawData: unknown): ReportNode | null => {
    if (!rawData) return null;
    const data = rawData as NodeData;
    let report: unknown = null;

    const processNode = (
        Array.isArray(data.document_submission_process)
            ? data.document_submission_process[0]
            : data.document_submission_process
    ) as NodeData | undefined;
    const nestedAliasedData = processNode?.aliased_data as NodeData | undefined;

    if (nestedAliasedData?.report_submission)
        report = nestedAliasedData.report_submission;
    else if (data.report_submission) report = data.report_submission;

    if (!report) return null;
    return Array.isArray(report)
        ? (report[0] as ReportNode)
        : (report as ReportNode);
};

const getFileNames = (fileData: unknown): string[] => {
    if (!fileData || typeof fileData !== 'object') return [];
    const typedData = fileData as Record<string, unknown>;
    const names: string[] = [];

    if (typedData.node_value && Array.isArray(typedData.node_value)) {
        for (const f of typedData.node_value) {
            const fileObj = f as Record<string, unknown>;
            const name =
                (fileObj.name as string) || (fileObj.file as File)?.name;
            if (name) names.push(name);
        }
        if (names.length > 0) return names;
    }

    if (typeof typedData.display_value === 'string') {
        try {
            const parsed = JSON.parse(typedData.display_value);
            if (Array.isArray(parsed)) {
                for (const f of parsed) {
                    const name = f?.name as string;
                    if (name) names.push(name);
                }
            }
        } catch {
            if (typedData.display_value) names.push(typedData.display_value);
        }
    }

    return names;
};
</script>

<template>
    <Step99_Review
        :is-submitted-view="isSubmittedView"
        :resource-data="resourceData"
    >
        <template #default="{ data, fields }">
            <GenericReviewSummary :fields="getFilteredFields(fields)" />

            <!-- Document Submission Files -->
            <FieldSet
                v-if="getReport(data)"
                legend="Document Submission"
                class="review-fieldset"
            >
                <div class="div-grid-cols">
                    <dt>Files</dt>
                    <dd>
                        <div
                            v-for="(fileName, i) in getFileNames(
                                getReport(data)?.aliased_data?.report_file,
                            )"
                            :key="i"
                            class="document-name-text"
                        >
                            <i
                                class="fa-regular fa-file"
                                style="color: #6c757d; margin-right: 0.5rem"
                            ></i>
                            {{ fileName }}
                        </div>
                        <div
                            v-if="
                                getFileNames(
                                    getReport(data)?.aliased_data?.report_file,
                                ).length === 0
                            "
                            style="color: #6c757d"
                        >
                            No files uploaded
                        </div>
                    </dd>
                </div>
            </FieldSet>

            <!-- Photographs -->
            <FieldSet
                v-if="getPhotos(data).length > 0"
                legend="Submission Photographs"
                class="review-fieldset"
            >
                <div
                    v-for="(photo, index) in getPhotos(data)"
                    :key="index"
                    class="div-grid-cols image-section"
                >
                    <dt>Image</dt>
                    <div class="image-wrapper">
                        <GenericWidget
                            graph-slug="document_submission"
                            node-alias="submission_photographs"
                            :mode="VIEW"
                            :should-show-label="false"
                            :aliased-node-data="
                                photo.aliased_data?.submission_photographs
                            "
                        />
                    </div>

                    <template v-if="photo.aliased_data?.photograph_description">
                        <dt>Description</dt>
                        <GenericWidget
                            graph-slug="document_submission"
                            node-alias="photograph_description"
                            :mode="VIEW"
                            :should-show-label="false"
                            :aliased-node-data="
                                photo.aliased_data?.photograph_description
                            "
                        />
                    </template>

                    <template v-if="photo.aliased_data?.photograph_view">
                        <dt>View</dt>
                        <GenericWidget
                            graph-slug="document_submission"
                            node-alias="photograph_view"
                            :mode="VIEW"
                            :should-show-label="false"
                            :aliased-node-data="
                                photo.aliased_data?.photograph_view
                            "
                        />
                    </template>

                    <template v-if="photo.aliased_data?.photographer">
                        <dt>Photographer</dt>
                        <GenericWidget
                            graph-slug="document_submission"
                            node-alias="photographer"
                            :mode="VIEW"
                            :should-show-label="false"
                            :aliased-node-data="
                                photo.aliased_data?.photographer
                            "
                        />
                    </template>

                    <template v-if="photo.aliased_data?.photograph_date">
                        <dt>Date</dt>
                        <GenericWidget
                            graph-slug="document_submission"
                            node-alias="photograph_date"
                            :mode="VIEW"
                            :should-show-label="false"
                            :aliased-node-data="
                                photo.aliased_data?.photograph_date
                            "
                        />
                    </template>
                </div>
            </FieldSet>
        </template>
    </Step99_Review>
</template>

<style scoped>
.review-fieldset {
    margin-top: 2rem;
}

.div-grid-cols {
    display: grid;
    grid-template-columns: 200px 1fr;
    gap: 1rem;
    margin-bottom: 2rem;
    padding-bottom: 2rem;
    border-bottom: 1px solid #eee;
    align-items: center;
}

.div-grid-cols:last-child {
    border-bottom: none;
    margin-bottom: 0;
    padding-bottom: 0;
}

dt {
    font-weight: bold;
    color: #000000;
}

dd {
    margin: 0;
    color: #000000;
}

.document-name-text {
    display: flex;
    align-items: center;
    margin-bottom: 0.25rem;
}

.image-wrapper :deep(img) {
    max-width: 100%;
    max-height: 250px;
    object-fit: contain;
    border-radius: 4px;
    border: 1px solid #ddd;
    background-color: #f8f9fa;
}
</style>
