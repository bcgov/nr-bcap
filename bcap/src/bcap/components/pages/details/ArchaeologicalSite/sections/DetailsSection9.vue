<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";
import EmptyState from "@/bcap/components/EmptyState.vue";
import { getDisplayValue, isEmpty } from "@/bcap/util.ts";
import StandardDataTable from "@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue";
import "primeicons/primeicons.css";
import type { RelatedDocumentsTile } from "@/bcap/schema/ArchaeologySiteSchema.ts";

const props = withDefaults(
    defineProps<{
        data: RelatedDocumentsTile | undefined;
        loading?: boolean;
        languageCode?: string;
    }>(),
    {
        languageCode: "en",
    },
);

const currentData = computed<RelatedDocumentsTile | undefined>(
    (): RelatedDocumentsTile | undefined => {
        return props.data?.aliased_data as RelatedDocumentsTile | undefined;
    },
);

const relatedDocumentsData = computed(() => {
    const docs = currentData.value?.related_site_documents;
    if (!docs) return [];
    return Array.isArray(docs) ? docs : [docs];
});

const referencesColumns = [
    { field: "reference_type", label: "Reference Type" },
    { field: "reference_title", label: "Title" },
    { field: "publication_year", label: "Year" },
    { field: "reference_authors", label: "Author(s)" },
    { field: "reference_remarks", label: "Remarks" },
];

const relatedDocumentsColumns = [
    { field: "related_document_type", label: "Document Type" },
    { field: "related_document_description", label: "Document Description" },
    { field: "related_site_documents", label: "Document" },
];

const imagesColumns = [
    { field: "image_type", label: "Image Type" },
    { field: "repository", label: "Repository" },
    { field: "photographer", label: "Photographer" },
    { field: "image_description", label: "Description" },
    { field: "image_caption", label: "Image Caption" },
    { field: "image_date", label: "Image Date" },
    { field: "modified_on", label: "Modified On" },
    { field: "modified_by", label: "Modified By" },
];

const otherMapsColumns = [
    { field: "map_name", label: "Map Name" },
    { field: "map_scale", label: "Map Scale" },
    { field: "modified_on", label: "Modified On" },
    { field: "modified_by", label: "Modified By" },
];

const hasReferences = computed(() => {
    return (
        currentData.value?.publication_reference &&
        currentData.value.publication_reference.length > 0
    );
});

const hasRelatedDocuments = computed(() => {
    return relatedDocumentsData.value && relatedDocumentsData.value.length > 0;
});

const hasImages = computed(() => {
    return (
        currentData.value?.site_images &&
        currentData.value.site_images.length > 0
    );
});

const hasOtherMaps = computed(() => {
    return (
        currentData.value?.other_maps && currentData.value.other_maps.length > 0
    );
});
</script>

<template>
    <DetailsSection
        section-title="9. References & Related Documents"
        :loading="props.loading"
        :visible="true"
    >
        <template #sectionContent>
            <DetailsSection
                section-title="References"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasReferences }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasReferences"
                        :table-data="currentData?.publication_reference ?? []"
                        :column-definitions="referencesColumns"
                        :initial-sort-field-index="2"
                    />
                    <EmptyState
                        v-else
                        message="No references available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Related Documents"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasRelatedDocuments }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasRelatedDocuments"
                        :table-data="relatedDocumentsData"
                        :column-definitions="relatedDocumentsColumns"
                        :initial-sort-field-index="0"
                    />
                    <EmptyState
                        v-else
                        message="No related documents available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Images"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasImages }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasImages"
                        :table-data="currentData?.site_images ?? []"
                        :column-definitions="imagesColumns"
                        :initial-sort-field-index="5"
                    />
                    <EmptyState
                        v-else
                        message="No images available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Other Maps"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasOtherMaps }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasOtherMaps"
                        :table-data="currentData?.other_maps ?? []"
                        :column-definitions="otherMapsColumns"
                        :initial-sort-field-index="2"
                    />
                    <EmptyState
                        v-else
                        message="No other maps available."
                    />
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>

<style scoped>
.empty-state {
    padding: 1rem;
    text-align: center;
    color: #6c757d;
    font-style: italic;
}
</style>
