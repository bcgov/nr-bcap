import { zodResolver } from '@primevue/forms/resolvers/zod';
import { getFlattenResolver } from '@/bcgov_arches_common/validation-utils.ts';
import * as z from 'zod';
import type { AliasedNodeData } from '@/arches_component_lab/types.ts';

// node_value shapes per datatype, keyed by the field that identifies each.
type ObjectNodeValue = {
    en?: { value?: string | null }; // string
    features?: unknown[]; // geojson
    resourceId?: string | null; // resource-instance
    url?: string | null; // url
};

export const isFilled = (
    value: AliasedNodeData | null | undefined,
): boolean => {
    const nodeValue = value?.node_value;
    if (nodeValue == null || nodeValue === '') return false;
    // string (date, concept uuid, non-localized), array (reference, file/resource lists).
    if (typeof nodeValue === 'string') return nodeValue.trim() !== '';
    if (Array.isArray(nodeValue)) return nodeValue.length > 0;

    if (typeof nodeValue === 'object') {
        const node = nodeValue as ObjectNodeValue;
        if (node.en) return !!node.en.value?.trim();
        if (node.features) return node.features.length > 0;
        if (node.resourceId !== undefined) return !!node.resourceId;
        if (node.url !== undefined) return !!node.url?.trim();
        return Object.keys(node).length > 0;
    }

    return true; // boolean, number
};

export const buildTileValidation = (tileSchema: z.ZodObject) => {
    const shape = tileSchema.shape as Record<string, z.ZodType>;
    const requiredAliases = Object.keys(shape).filter(
        (alias) => !shape[alias].safeParse(undefined).success,
    );

    const resolverSchema = z.object(
        Object.fromEntries(
            requiredAliases.map((alias) => [
                alias,
                z.custom<AliasedNodeData>((v) => isFilled(v as AliasedNodeData), {
                    message: 'This field is required.',
                }),
            ]),
        ),
    );
    const baseResolver = zodResolver(resolverSchema);
    const resolver = getFlattenResolver(baseResolver) as typeof baseResolver;

    const isComplete = (
        tileAliasedData: Record<string, AliasedNodeData | null> | undefined,
    ) => requiredAliases.every((alias) => isFilled(tileAliasedData?.[alias]));

    return { resolver, requiredAliases, isComplete };
};
