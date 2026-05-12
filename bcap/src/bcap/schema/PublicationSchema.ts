import type {
    AliasedNodeData,
    AliasedTileData,
} from '@/arches_component_lab/types.ts';
import type { FileListValue } from '@/arches_component_lab/datatypes/file-list/types.ts';
import type { ArchesResourceInstanceData } from '@/bcgov_arches_common/types.ts';
import type { ReferenceSelectValue } from '@/arches_controlled_lists/datatypes/reference-select/types.ts';
import type { DateValue } from '@/arches_component_lab/datatypes/date/types.ts';
import type { StringValue } from '@/arches_component_lab/datatypes/string/types.ts';

export interface AuthorsTile extends AliasedTileData {
    aliased_data: {
        authors?: ReferenceSelectValue;
        other_authors_unlisted?: StringValue;
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
        information_carrier?: FileListValue;
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
        title?: AliasedNodeData;
        year_of_publication?: DateValue;
        reference_authors?: AliasedNodeData;
        reference_remarks?: AliasedNodeData;
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
