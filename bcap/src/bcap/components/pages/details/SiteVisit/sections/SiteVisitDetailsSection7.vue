<script setup lang="ts">
import { computed, toRef } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import EmptyState from '@/bcap/components/EmptyState.vue';
import StandardDataTable from '@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue';
import { useTileEditLog } from '@/bcgov_arches_common/composables/useTileEditLog.ts';
import type { EditLogData } from '@/bcgov_arches_common/types.ts';
import type { ColumnDefinition } from '@/bcgov_arches_common/components/StandardDataTable/types.ts';
import { expandDocumentRows } from '@/bcgov_arches_common/utils/document.ts';
import { formatFilenameUrl } from '@/bcgov_arches_common/datatypes/file-list/utils.ts';
import type {
    SiteVisitSchema,
    SiteVisitRelatedDocumentsTile,
} from '@/bcap/schema/SiteVisitSchema.ts';

const props = withDefaults(
    defineProps<{
        data: SiteVisitSchema | undefined;
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

const currentData = computed<SiteVisitRelatedDocumentsTile | undefined>(() => {
    return props.data?.aliased_data?.related_documents?.aliased_data as
        | SiteVisitRelatedDocumentsTile
        | undefined;
});

const relatedDocumentsData = computed(() => {
    const documents = currentData.value?.related_site_documents;
    if (!documents) return [];
    const documentsArray = Array.isArray(documents) ? documents : [documents];
    return expandDocumentRows(documentsArray, 'related_site_documents');
});

const referencesColumns: ColumnDefinition[] = [
    { field: 'reference_type', label: 'Reference Type' },
    { field: 'reference_title', label: 'Title' },
    { field: 'reference_year', label: 'Year' },
    { field: 'reference_authors', label: 'Author(s)' },
    { field: 'reference_remarks', label: 'Remarks' },
];

const relatedDocumentsColumns = computed<ColumnDefinition[]>(() => {
    return [
        {
            field: 'related_site_documents',
            label: 'Document',
            isHtml: true,
            displayFunction: formatFilenameUrl,
        },
        { field: 'related_document_type', label: 'Document Type' },
        {
            field: 'related_document_description',
            label: 'Document Description',
            isHtml: true,
        },
    ];
});

const imagesColumns = computed<ColumnDefinition[]>(() => {
    return [
        {
            field: 'site_images',
            label: 'Image',
            isHtml: true,
            displayFunction: formatFilenameUrl,
        },
        { field: 'image_type', label: 'Image Type' },
        { field: 'image_view', label: 'Image View' },
        { field: 'photographer', label: 'Photographer' },
        { field: 'image_description', label: 'Description', isHtml: true },
        { field: 'image_features', label: 'Image Features' },
        { field: 'copyright', label: 'Copyright' },
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
</script>

<template>
    <DetailsSection
        section-title="7. References & Related Documents"
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
                section-title="Site Images"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasImages }"
            >
                <template #sectionContent>
                    <StandardDataTable
                        v-if="hasImages"
                        :table-data="siteImagesTableData"
                        :column-definitions="imagesColumns"
                        :initial-sort-field-index="0"
                    />
                    <EmptyState
                        v-else
                        message="No site images available."
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
