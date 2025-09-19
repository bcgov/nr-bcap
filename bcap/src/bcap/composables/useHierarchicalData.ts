import { ref, watch, type Ref } from "vue";
import type {
    AliasedTileData,
    AliasedNodeData,
} from "@/arches_component_lab/types.ts";

interface HierarchicalFieldConfig {
    sourceField: string;
    hierarchicalFields: string[];
    flatFields?: string[];
}

async function fetchHierarchy(listItemId: string): Promise<string[]> {
    try {
        const response = await fetch(`/bcap/api/hierarchy/${listItemId}/`);

        if (!response.ok) {
            console.error(
                `Failed to fetch hierarchy for ${listItemId}: ${response.status}`,
            );
            return [];
        }

        const data = await response.json();
        return data.labels || [];
    } catch (error) {
        console.error(`API error for ${listItemId}:`, error);
        return [];
    }
}

export function useHierarchicalData(
    dataSource: Ref<AliasedTileData[] | undefined>,
    config: HierarchicalFieldConfig,
) {
    const processedData = ref<AliasedTileData[]>([]);
    const isProcessing = ref(false);

    async function loadData() {
        if (!dataSource.value || !dataSource.value.length) {
            processedData.value = [];
            return;
        }

        isProcessing.value = true;

        try {
            const results = await Promise.all(
                dataSource.value.map(
                    async (item: AliasedTileData, index: number) => {
                        let listItemId = null;

                        const originalData = (item.aliased_data ||
                            item) as Record<
                            string,
                            AliasedNodeData | undefined
                        >;
                        const sourceNode = originalData[config.sourceField] as
                            | AliasedNodeData
                            | undefined;

                        if (
                            sourceNode?.node_value &&
                            Array.isArray(sourceNode.node_value) &&
                            sourceNode.node_value[0]?.uri
                        ) {
                            const uriMatch =
                                sourceNode.node_value[0].uri.match(
                                    /item\/([a-f0-9-]+)$/,
                                );

                            if (uriMatch) {
                                listItemId = uriMatch[1];
                            }
                        }

                        let hierarchy: string[] = [];

                        if (listItemId) {
                            hierarchy = await fetchHierarchy(listItemId);
                        }

                        if (!hierarchy.length && sourceNode?.display_value) {
                            hierarchy = [sourceNode.display_value];
                        }

                        const aliasedData: Record<string, AliasedNodeData> = {};

                        config.hierarchicalFields.forEach((field, idx) => {
                            aliasedData[field] = {
                                node_value: hierarchy[idx] || null,
                                display_value: hierarchy[idx] || "",
                                details: [],
                            };
                        });

                        config.flatFields?.forEach((field) => {
                            const fieldData = originalData[field];

                            aliasedData[field] = fieldData || {
                                node_value: null,
                                display_value: "",
                                details: [],
                            };
                        });

                        const transformedRow: AliasedTileData = {
                            tileid:
                                item.tileid || `${config.sourceField}-${index}`,
                            resourceinstance: item.resourceinstance,
                            nodegroup: item.nodegroup,
                            parenttile: item.parenttile,
                            sortorder: item.sortorder || index,
                            provisionaledits: item.provisionaledits,
                            aliased_data: aliasedData,
                        };

                        return transformedRow;
                    },
                ),
            );

            processedData.value = results;
        } catch (error) {
            console.error(
                `Error processing ${config.sourceField} data:`,
                error,
            );
            processedData.value = [];
        } finally {
            isProcessing.value = false;
        }
    }

    watch(
        dataSource,
        (newVal) => {
            if (newVal) {
                loadData();
            }
        },
        { immediate: true },
    );

    return {
        processedData,
        isProcessing,
        reload: loadData,
    };
}
