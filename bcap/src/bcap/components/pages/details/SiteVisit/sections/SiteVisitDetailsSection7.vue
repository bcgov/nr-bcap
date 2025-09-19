<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";
import EmptyState from "@/bcap/components/EmptyState.vue";
import StandardDataTable from "@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue";
import type { SiteVisitSchema } from "@/bcap/schema/SiteVisitSchema.ts";

const props = withDefaults(
    defineProps<{ data: SiteVisitSchema | undefined; loading?: boolean }>(),
    { loading: false },
);

const referencesData = computed(() => {
    return (
        props.data?.aliased_data?.references_and_documents?.aliased_data
            ?.references || []
    );
});

const documentsData = computed(() => {
    return (
        props.data?.aliased_data?.references_and_documents?.aliased_data
            ?.related_documents || []
    );
});

const photosData = computed(() => {
    return (
        props.data?.aliased_data?.references_and_documents?.aliased_data
            ?.photos || []
    );
});

const hasReferences = computed(() => {
    return referencesData.value && referencesData.value.length > 0;
});

const hasDocuments = computed(() => {
    return documentsData.value && documentsData.value.length > 0;
});

const hasPhotos = computed(() => {
    return photosData.value && photosData.value.length > 0;
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

const photosColumns = [
    { field: "photo_title", label: "Photo Title" },
    { field: "photo_description", label: "Description" },
    { field: "photographer", label: "Photographer" },
    { field: "photo_date", label: "Date" },
];
</script>

<template>
    <DetailsSection
        section-title="7. References & Related Documents"
        :visible="true"
        :loading="props.loading"
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
                        :table-data="referencesData"
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
                :class="{ 'empty-section': !hasDocuments }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasDocuments"
                        :table-data="documentsData"
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
                section-title="Photos"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasPhotos }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasPhotos"
                        :table-data="photosData"
                        :column-definitions="photosColumns"
                        :initial-sort-field-index="3"
                    />
                    <EmptyState
                        v-else
                        message="No photos available."
                    />
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>
