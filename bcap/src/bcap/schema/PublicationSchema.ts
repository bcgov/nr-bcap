import type {
    AliasedNodeData,
    AliasedTileData,
} from '@/arches_vue_components/types.ts';
import type { FileListAliasedNodeData } from '@/arches_vue_components/datatypes/file-list/types.ts';
import type { ArchesResourceInstanceData } from '@/bcgov_arches_common/types.ts';
import type { ReferenceSelectAliasedNodeData } from '@/arches_controlled_lists/datatypes/reference-select/types.ts';
import type { DateAliasedNodeData } from '@/arches_vue_components/datatypes/date/types.ts';
import type { StringAliasedNodeData } from '@/arches_vue_components/datatypes/string/types.ts';

export interface AuthorsTile extends AliasedTileData {
    aliased_data: {
        authors?: ReferenceSelectAliasedNodeData;
        other_authors_unlisted?: StringAliasedNodeData;
    };
}

export interface CopyrightTypeTile extends AliasedTileData {
    aliased_data: {
        distribution_permitted?: AliasedNodeData;
        signed_agreement?: AliasedNodeData;
        agreement_text?: AliasedNodeData;
        copyright_type?: AliasedNodeData;
    };
}

export interface InformationCarrierTile extends AliasedTileData {
    aliased_data: {
        information_carrier?: FileListAliasedNodeData;
    };
}

export interface KeywordTile extends AliasedTileData {
    aliased_data: {
        keyword?: AliasedNodeData;
    };
}

export interface PublicationDetailsTile extends AliasedTileData {
    aliased_data: {
        publication_type?: AliasedNodeData;
        title?: StringAliasedNodeData;
        year_of_publication?: DateAliasedNodeData;
        page_range_start?: AliasedNodeData;
        page_range_end?: AliasedNodeData;
        publication_remarks?: StringAliasedNodeData;
        journal_or_volume_name?: AliasedNodeData;
        other_journal_or_volume_name?: StringAliasedNodeData;
    };
}
export interface ReferenceLinkTile extends AliasedTileData {
    aliased_data: {
        archaeological_sites?: AliasedNodeData;
        site_visits?: AliasedNodeData;
        repositories?: AliasedNodeData;
    };
}

type PublicationAliasedData = {
    authors?: AuthorsTile;
    copyright_type?: CopyrightTypeTile;
    information_carrier?: InformationCarrierTile;
    keyword: KeywordTile[];
    publication_details?: PublicationDetailsTile;
    reference_link?: ReferenceLinkTile;
};

export interface PublicationSchema extends ArchesResourceInstanceData<PublicationAliasedData> {
    aliased_data: PublicationAliasedData;
}
