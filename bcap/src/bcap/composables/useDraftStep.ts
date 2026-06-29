import { inject, type Ref } from 'vue';
import * as z from 'zod';
import { updateDraftValue } from '@/bcap/util.ts';
import { buildTileValidation } from '@/bcap/validation.ts';
import type { AliasedNodeData } from '@/arches_component_lab/types.ts';
import type { ArchesDraftData } from '@/bcap/types.ts';

// Shared wiring for a permit workflow step: draft injection, the inline-error
// resolver, required-field gating, and the value-update handler. validationTile
// is the tile whose required fields gate the step.
export function useDraftStep(
    graphSlug: string,
    tileSchema: z.ZodObject,
    validationTile: string,
    emit: (event: 'update:step-is-valid', valid: boolean) => void,
) {
    const draftId = inject<Ref<string | null>>('draftId');
    const draftData = inject<Ref<ArchesDraftData>>('draftData');
    const { resolver, isComplete } = buildTileValidation(tileSchema);

    const isValid = () =>
        isComplete(draftData?.value?.[validationTile]?.aliased_data);

    const updateValue = (
        newValue: AliasedNodeData,
        attribute_name: string,
        node_group_alias: string | string[],
    ) => {
        updateDraftValue(
            draftData?.value,
            draftId?.value,
            graphSlug,
            newValue,
            attribute_name,
            node_group_alias,
        );
        emit('update:step-is-valid', isValid());
    };

    return { draftData, resolver, isValid, updateValue };
}
