<script setup lang="ts">
import { computed, toRef, type Ref, watchEffect } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import EmptyState from '@/bcap/components/EmptyState.vue';
import StandardDataTable from '@/bcgov_arches_common/components/StandardDataTable/StandardDataTable.vue';
import { useTileEditLog } from '@/bcgov_arches_common/composables/useTileEditLog.ts';
import type {
    AliasedTileDataWithAudit,
    EditLogData,
} from '@/bcgov_arches_common/types.ts';
import type {
    AliasedNodeData,
    AliasedTileData,
} from '@/arches_vue_components/types.ts';
import 'primeicons/primeicons.css';
import type {
    PublicationPublicationDetailsTile,
    Publication,
    PublicationAuthorsTile,
    ArchaeologicalSiteRelatedDocumentsTile,
    ArchaeologicalSiteRelatedDocumentsAliasedData,
    SiteVisit,
} from '@/bcap/client/types.gen.ts';
import type { HriaDiscontinuedData } from '@/bcap/client/types.gen.ts';
import type { ColumnDefinition } from '@/bcgov_arches_common/components/StandardDataTable/types.ts';
import { expandDocumentRows } from '@/bcgov_arches_common/utils/document.ts';
import { formatFilenameUrl } from '@/bcgov_arches_common/datatypes/file-list/utils.ts';
import { isEmpty } from '@/bcap/util.ts';

const props = withDefaults(
    defineProps<{
        data: ArchaeologicalSiteRelatedDocumentsTile | undefined;
        siteVisitData: SiteVisit[];
        hriaData?: HriaDiscontinuedData;
        publicationData?: Publication[] | undefined;
        siteVisitPublicationData?: Publication[] | undefined;
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
        hriaData: undefined,
        publicationData: undefined,
        siteVisitPublicationData: undefined,
    },
);

const currentData = computed<
    ArchaeologicalSiteRelatedDocumentsAliasedData | undefined
>((): ArchaeologicalSiteRelatedDocumentsAliasedData | undefined => {
    return props.data?.aliased_data;
});

const relatedDocumentsData = computed(() => {
    let documents: AliasedTileData[] = [];

    if (props.siteVisitData?.length) {
        const siteVisitDocuments = props.siteVisitData.flatMap(
            (visit) =>
                visit?.aliased_data?.related_documents?.aliased_data
                    ?.related_site_documents ?? [],
        );
        documents = expandDocumentRows(
            siteVisitDocuments as unknown as AliasedTileData[],
            'related_documents',
        );
    }

    const docs = currentData.value?.related_site_documents;
    if (docs) {
        const docsArray = Array.isArray(docs) ? docs : [docs];
        documents = [
            ...documents,
            ...expandDocumentRows(
                docsArray as unknown as AliasedTileData[],
                'related_site_documents',
            ),
        ];
    }
    return documents;
});

watchEffect(() =>
    console.log('relatedDocumentsData', relatedDocumentsData.value.length),
);

type PublicationDetailsTileWithAuthors = AliasedTileDataWithAudit &
    PublicationPublicationDetailsTile & {
        aliased_data: PublicationPublicationDetailsTile['aliased_data'] & {
            authors: PublicationAuthorsTile[] | undefined;
        };
    };

const publicationReferencesData = computed<PublicationDetailsTileWithAuthors[]>(
    () => {
        let publications: Publication[] = [];

        if (props.siteVisitPublicationData?.length) {
            publications = [...props.siteVisitPublicationData];
        }

        if (props.publicationData?.length) {
            const seenIds = new Set(
                publications.map((p) => p.resourceinstanceid),
            );
            publications = [
                ...publications,
                ...props.publicationData.filter(
                    (p) => !seenIds.has(p.resourceinstanceid),
                ),
            ];
        }

        return publications.map((publication) => {
            let data = publication.aliased_data
                ?.publication_details as PublicationDetailsTileWithAuthors;
            data.aliased_data.authors =
                publication.aliased_data?.authors ?? undefined;
            return data;
        });
    },
);

const publicationColumns: ColumnDefinition[] = [
    {
        field: 'publication_type',
        label: 'Reference Type',
    },
    { field: 'title', label: 'Title' },
    {
        field: 'year_of_publication',
        label: 'Year',
    },
    {
        field: 'authors.0.aliased_data.authors',
        label: 'Author(s)',
        displayFunction: (value: AliasedTileDataWithAudit) =>
            (value.aliased_data?.authors as PublicationAuthorsTile[])
                ?.map((author) => author?.aliased_data?.authors?.display_value)
                .join(', '),
    },
    {
        label: 'Remarks',
        field: 'publication_remarks',
        isHtml: true,
    },
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
        { field: 'other_maps_map_name', label: 'Map Name' },
        { field: 'other_maps_map_scale', label: 'Map Scale' },
        {
            field: 'other_maps_modified_on',
            label: 'Modified On',
            visible: props.showAuditFields,
        },
        {
            field: 'other_maps_modified_by',
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

const siteImagesData = computed(() => {
    let images: AliasedTileData[] = [];

    if (props.siteVisitData?.length) {
        images = props.siteVisitData.flatMap(
            (visit) =>
                visit?.aliased_data?.related_documents?.aliased_data
                    ?.site_images ?? [],
        ) as unknown as AliasedTileData[];
    }

    const asSiteImages = currentData.value?.site_images;
    if (asSiteImages?.length) {
        images = [...images, ...(asSiteImages as unknown as AliasedTileData[])];
    }

    return images;
});

const { processedData: siteImagesTableData } = useTileEditLog(
    siteImagesData as Ref<AliasedTileData[]>,
    toRef(props, 'editLogData'),
);

const hasImages = computed(() => siteImagesTableData.value.length > 0);

const otherMapsData = computed<AliasedTileDataWithAudit[]>(() => {
    const hriaData = props.hriaData as HriaDiscontinuedData | undefined;
    const maps = hriaData?.aliased_data?.other_maps;
    if (!maps) return [];
    return (Array.isArray(maps)
        ? maps
        : [maps]) as unknown as AliasedTileDataWithAudit[];
});

const hasOtherMaps = computed(() => {
    return otherMapsData.value.length > 0;
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
                        :table-data="publicationReferencesData"
                        :column-definitions="publicationColumns"
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
                        :table-data="otherMapsData"
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
