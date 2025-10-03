import { ref, watch, type Ref } from 'vue';
import type {
    AliasedTileData,
    AliasedNodegroupData,
} from '@/arches_component_lab/types.ts';
import type {
    EditLogData,
    AliasedTileDataWithAudit,
    AliasedNodeDataWithAudit,
} from '@/bcgov_arches_common/types.ts';
import {
    DEFAULT_ENTERED_ON_FIELD,
    DEFAULT_ENTERED_BY_FIELD,
} from '@/bcgov_arches_common/constants.ts';

export function applyEditLogToTile(
    tile: AliasedTileData,
    editLogData: EditLogData | undefined,
): AliasedTileDataWithAudit {
    const tileEditData = tile.tileid
        ? editLogData?.[`tile_${tile.tileid}`]
        : undefined;

    if (
        !tileEditData?.[DEFAULT_ENTERED_ON_FIELD] &&
        !tileEditData?.[DEFAULT_ENTERED_BY_FIELD]
    ) {
        return {
            ...tile,
            aliased_data: tile.aliased_data as Record<
                string,
                AliasedNodeDataWithAudit | AliasedNodegroupData | null
            >,
        } as AliasedTileDataWithAudit;
    }

    return {
        ...tile,
        aliased_data: tile.aliased_data as Record<
            string,
            AliasedNodeDataWithAudit | AliasedNodegroupData | null
        >,
        audit: {
            [DEFAULT_ENTERED_ON_FIELD]: tileEditData[DEFAULT_ENTERED_ON_FIELD],
            [DEFAULT_ENTERED_BY_FIELD]: tileEditData[DEFAULT_ENTERED_BY_FIELD],
        },
    } as AliasedTileDataWithAudit;
}

export function useTileEditLog(
    sourceData: Ref<AliasedTileData[] | undefined>,
    editLogData: Ref<EditLogData | undefined>,
) {
    const processedData = ref<AliasedTileDataWithAudit[]>([]);

    watch(
        () => [sourceData.value, editLogData.value],
        () => {
            const items = sourceData.value || [];

            processedData.value = items.map((item) =>
                applyEditLogToTile(item, editLogData.value),
            );
        },
        { immediate: true, deep: true },
    );

    return {
        processedData,
    };
}

export function useSingleTileEditLog(
    sourceData: Ref<AliasedTileData | undefined>,
    editLogData: Ref<EditLogData | undefined>,
) {
    const processedData = ref<AliasedTileDataWithAudit | null>(null);

    watch(
        () => [sourceData.value, editLogData.value],
        () => {
            if (!sourceData.value) {
                processedData.value = null;
                return;
            }

            processedData.value = applyEditLogToTile(
                sourceData.value,
                editLogData.value,
            );
        },
        { immediate: true, deep: true },
    );

    return {
        processedData,
    };
}

export function collectTileIds(data: unknown, paths: string[][]): string[] {
    const tileIds: string[] = [];

    const collectFromValue = (value: unknown) => {
        if (!value) return;

        if (Array.isArray(value)) {
            value.forEach((item) => {
                const tileData = item as AliasedTileData;

                if (tileData?.tileid) {
                    tileIds.push(tileData.tileid);
                }
            });
        } else {
            const tileData = value as AliasedTileData;

            if (tileData?.tileid) {
                tileIds.push(tileData.tileid);
            }
        }
    };

    paths.forEach((path) => {
        let current: unknown = data;

        for (const key of path) {
            if (!current || typeof current !== 'object') break;
            current = (current as Record<string, unknown>)[key];
        }

        collectFromValue(current);
    });

    return tileIds;
}
