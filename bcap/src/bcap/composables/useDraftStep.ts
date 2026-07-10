import { storeToRefs } from 'pinia';
import * as z from 'zod';
import { buildTileValidation } from '@/bcap/validation.ts';
import { useDraftStore } from '@/bcap/stores/draft.ts';
import type { AliasedNodeData } from '@/arches_component_lab/types.ts';

// Per-step form glue, kept out of the global draft store because validation is
// per-step: each step validates its own tile against its own schema. Pairs the
// shared draft with one step's resolver and required-field gating (omit the
// schema to skip validation). emit fires step validity after each edit so the
// stepper can gate navigation.
export function useDraftStep(
    tileSchema?: z.ZodObject,
    validationTile?: string,
    emit?: (event: 'update:step-is-valid', valid: boolean) => void,
) {
    const store = useDraftStore();
    const { draftData } = storeToRefs(store);
    const validation = tileSchema ? buildTileValidation(tileSchema) : null;

    const isValid = () =>
        validation && validationTile
            ? validation.isComplete(
                  draftData.value?.[validationTile]?.aliased_data,
              )
            : true;

    const updateValue = (
        newValue: AliasedNodeData,
        attribute_name: string,
        node_group_alias: string | string[],
    ) => {
        store.updateValue(newValue, attribute_name, node_group_alias);
        emit?.('update:step-is-valid', isValid());
    };

    return { draftData, resolver: validation?.resolver, isValid, updateValue };
}
