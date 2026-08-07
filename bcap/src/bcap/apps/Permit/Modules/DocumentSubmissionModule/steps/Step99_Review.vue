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

// Filters out only photographs so the generic component handles everything else
const getFilteredFields = (fields: unknown) => {
    if (!Array.isArray(fields)) return [];

    return fields.filter((f) => {
        const alias = f.alias || f.nodeAlias || f.node?.alias || f.node_alias;
        return alias !== 'submission_photographs';
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

    if (nestedAliasedData?.submission_photographs) {
        photos = nestedAliasedData.submission_photographs;
    } else if (data.submission_photographs) {
        photos = data.submission_photographs;
    }

    if (!photos) return [];

    return Array.isArray(photos)
        ? (photos as PhotographNode[])
        : [photos as PhotographNode];
};
</script>

<template>
    <Step99_Review
        :is-submitted-view="isSubmittedView"
        :resource-data="resourceData"
    >
        <template #default="{ data, fields }">
            <GenericReviewSummary :fields="getFilteredFields(fields)" />

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

/* 
  selector to shrink images
*/
.image-wrapper :deep(img) {
    max-width: 100%;
    max-height: 250px;
    object-fit: contain;
    border-radius: 4px;
    border: 1px solid #ddd;
    background-color: #f8f9fa;
}
</style>
