import { storeToRefs } from 'pinia';
import * as z from 'zod';
import type { Ref } from 'vue';
import { buildTileValidation } from '@/bcap/validation.ts';
import { useDraftStore } from '@/bcap/stores/draft.ts';
import type { ArchesDraftData } from '@/bcap/types.ts';
import type { AliasedNodeData } from '@/arches_vue_components/types.ts';

// Per-step form glue, kept out of the global draft store because validation is
// per-step: each step validates its own tile against its own schema. Pairs the
// shared draft with one step's resolver and required-field gating (omit the
// schema to skip validation). emit fires step validity after each edit so the
// stepper can gate navigation.
//
// The optional type parameter T narrows draftData to the aliased data type for
// the graph the step belongs to, enabling TypeScript to catch invalid node
// aliases at compile time. Defaults to ArchesDraftData (untyped) so existing
// callers that don't pass T are unaffected.
export function useDraftStep<T = ArchesDraftData>(
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

    return {
        // @todo - should this be removed?
        // Typed as ArchesDraftData so DraftNode (which extends AliasedNodeData)
        // flows through to GenericWidget :aliased-node-data bindings without error.
        draftData,
        // Typed as T for computed properties and conditional logic, where alias
        // correctness matters. The generated resource types have display_value?:
        // string (optional) rather than display_value: string, making them
        // incompatible with GenericWidget's AliasedNodeData prop — so only use
        // this ref in script/computed code, not in template widget bindings.
        typedDraftData: draftData as unknown as Ref<T>,
        resolver: validation?.resolver,
        isValid,
        updateValue,
    };
}
