<script setup lang="ts">
import { computed, toRef } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import EmptyState from '@/bcap/components/EmptyState.vue';
import StandardDataTable from '@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue';
import { useTileEditLog } from '@/bcgov_arches_common/composables/useTileEditLog.ts';
import type { EditLogData } from '@/bcgov_arches_common/types.ts';
import 'primeicons/primeicons.css';
import type { RelatedDocumentsTile } from '@/bcap/schema/ArchaeologySiteSchema.ts';
import type { ColumnDefinition } from '@/bcgov_arches_common/components/StandardDataTable/types.ts';

const props = withDefaults(
    defineProps<{
        data: RelatedDocumentsTile | undefined;
        loading?: boolean;
        languageCode?: string;
        forceCollapsed?: boolean;
        editLogData?: EditLogData;
        showAuditFields?: boolean;
    }>(),
    {
        languageCode: 'en',
        loading: false,
        forceCollapsed: undefined,
        editLogData: () => ({}),
        showAuditFields: false,
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

const referencesColumns: ColumnDefinition[] = [
    { field: 'reference_type', label: 'Reference Type' },
    { field: 'reference_title', label: 'Title' },
    { field: 'publication_year', label: 'Year' },
    { field: 'reference_authors', label: 'Author(s)' },
    { field: 'reference_remarks', label: 'Remarks' },
];

const relatedDocumentsColumns = computed<ColumnDefinition[]>(() => {
    return [
        { field: 'related_document_type', label: 'Document Type' },
        {
            field: 'related_document_description',
            label: 'Document Description',
            isHtml: true,
        },
        { field: 'related_site_documents', label: 'Document' },
    ];
});

const imagesColumns = computed<ColumnDefinition[]>(() => {
    return [
        { field: 'image_type', label: 'Image Type' },
        { field: 'repository', label: 'Repository' },
        { field: 'photographer', label: 'Photographer' },
        { field: 'image_description', label: 'Description', isHtml: true },
        { field: 'image_caption', label: 'Image Caption' },
        { field: 'image_date', label: 'Image Date' },
        {
            field: 'entered_on',
            label: 'Modified On',
            visible: props.showAuditFields,
        },
        {
            field: 'entered_by',
            label: 'Modified By',
            visible: props.showAuditFields,
        },
    ];
});

const otherMapsColumns = computed<ColumnDefinition[]>(() => {
    return [
        { field: 'map_name', label: 'Map Name' },
        { field: 'map_scale', label: 'Map Scale' },
        {
            field: 'entered_on',
            label: 'Modified On',
            visible: props.showAuditFields,
        },
        {
            field: 'entered_by',
            label: 'Modified By',
            visible: props.showAuditFields,
        },
    ];
});

const hasReferences = computed(() => {
    return (
        currentData.value?.publication_reference &&
        currentData.value.publication_reference.length > 0
    );
});

const hasRelatedDocuments = computed(() => {
    return relatedDocumentsData.value && relatedDocumentsData.value.length > 0;
});

const siteImagesData = computed(() => currentData.value?.site_images || []);

const { processedData: siteImagesTableData } = useTileEditLog(
    siteImagesData,
    toRef(props, 'editLogData'),
);

const hasImages = computed(() => siteImagesTableData.value.length > 0);

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
        :force-collapsed="props.forceCollapsed"
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
                        :table-data="siteImagesTableData"
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
