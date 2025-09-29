import { ref, watch, type Ref } from 'vue';
import type { AliasedTileData, AliasedNodeData } from '@/arches_component_lab/types.ts';

export interface EditLogEntry {
    entered_on: string | null;
    entered_by: string | null;
}

export type EditLogData = Record<string, EditLogEntry>;

export function applyEditLogToTile(
    tile: AliasedTileData,
    editLogData: EditLogData | undefined,
    enteredOnField = 'entered_on',
    enteredByField = 'entered_by'
): AliasedTileData {
    const tileEditData = tile.tileid ? editLogData?.[`tile_${tile.tileid}`] : undefined;

    if (!tileEditData?.entered_on && !tileEditData?.entered_by) {
        return tile;
    }

    const updatedAliasedData = { ...(tile.aliased_data || {}) };

    if (tileEditData?.entered_on) {
        updatedAliasedData[enteredOnField] = {
            node_value: tileEditData.entered_on,
            display_value: tileEditData.entered_on,
            details: []
        } as AliasedNodeData;
    }

    if (tileEditData?.entered_by) {
        updatedAliasedData[enteredByField] = {
            node_value: tileEditData.entered_by,
            display_value: tileEditData.entered_by,
            details: []
        } as AliasedNodeData;
    }

    return {
        ...tile,
        aliased_data: updatedAliasedData
    };
}

export function useTileEditLog(
    sourceData: Ref<AliasedTileData[] | undefined>,
    editLogData: Ref<EditLogData | undefined>,
    options?: {
        enteredOnField?: string;
        enteredByField?: string;
    }
) {
    const processedData = ref<AliasedTileData[]>([]);

    const enteredOnField = options?.enteredOnField || 'entered_on';
    const enteredByField = options?.enteredByField || 'entered_by';

    watch(
        () => [sourceData.value, editLogData.value],
        () => {
            const items = sourceData.value || [];

            processedData.value = items.map((item: AliasedTileData) =>
                applyEditLogToTile(item, editLogData.value, enteredOnField, enteredByField)
            );
        },
        { immediate: true, deep: true }
    );

    return {
        processedData
    };
}

export function useSingleTileEditLog(
    sourceData: Ref<AliasedTileData | undefined>,
    editLogData: Ref<EditLogData | undefined>,
    options?: {
        enteredOnField?: string;
        enteredByField?: string;
    }
) {
    const processedData = ref<AliasedTileData | null>(null);

    const enteredOnField = options?.enteredOnField || 'entered_on';
    const enteredByField = options?.enteredByField || 'entered_by';

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
                enteredOnField,
                enteredByField
            );
        },
        { immediate: true, deep: true }
    );

    return {
        processedData
    };
}

export function collectTileIds(data: unknown, paths: string[][]): string[] {
    const tileIds: string[] = [];

    const collectFromValue = (value: unknown) => {
        if (!value) return;

        if (Array.isArray(value)) {
            value.forEach(item => {
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

    paths.forEach(path => {
        let current: unknown = data;

        for (const key of path) {
            if (!current || typeof current !== 'object') break;
            current = (current as Record<string, unknown>)[key];
        }

        collectFromValue(current);
    });

    return tileIds;
}
