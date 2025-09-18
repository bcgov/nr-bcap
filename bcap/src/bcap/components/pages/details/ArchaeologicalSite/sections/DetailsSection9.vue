<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";
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
    { field: "related_document_type", label: "Type" },
    { field: "related_site_documents", label: "Document" },
    { field: "related_document_description", label: "Description" },
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
</script>

<template>
    <DetailsSection
        section-title="9. References & Related Documents"
        :loading="props.loading"
        :visible="true"
    >
        <template #sectionContent>
            <DetailsSection
                section-title="9.1 References"
                :visible="true"
            >
                <template #sectionContent>
                    <StandardDataTable
                        :table-data="currentData?.publication_reference ?? []"
                        :column-definitions="referencesColumns"
                        title="Publication References"
                        :initial-sort-field-index="2"
                    />
                    <div v-if="!currentData?.publication_reference?.length">
                        <p>No references available.</p>
                    </div>
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="9.2 Related Documents"
                :visible="true"
            >
                <template #sectionContent>
                    <StandardDataTable
                        :table-data="relatedDocumentsData"
                        :column-definitions="relatedDocumentsColumns"
                        title="Site Documents"
                        :initial-sort-field-index="0"
                    />
                    <div v-if="!relatedDocumentsData.length">
                        <p>No related documents available.</p>
                    </div>
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="9.3 Images"
                :visible="true"
            >
                <template #sectionContent>
                    <StandardDataTable
                        :table-data="currentData?.site_images ?? []"
                        :column-definitions="imagesColumns"
                        title="Site Images"
                        :initial-sort-field-index="5"
                    />
                    <div v-if="!currentData?.site_images?.length">
                        <p>No images available.</p>
                    </div>
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="9.4 Other Maps"
                :visible="true"
            >
                <template #sectionContent>
                    <StandardDataTable
                        :table-data="currentData?.other_maps ?? []"
                        :column-definitions="otherMapsColumns"
                        title="Other Maps"
                        :initial-sort-field-index="2"
                    />
                    <div v-if="!currentData?.other_maps?.length">
                        <p>No other maps available.</p>
                    </div>
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
