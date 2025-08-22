import type { AliasedNodeData } from "@/arches_component_lab/types.ts";
export const getDisplayValue = (value: AliasedNodeData) => {
    return value?.node_value ? value.display_value : "";
};

export const isEmpty = (value: AliasedNodeData) => {
    return !value?.node_value;
};
