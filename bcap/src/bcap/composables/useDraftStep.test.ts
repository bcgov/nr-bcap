import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ref, defineComponent, h } from 'vue';
import { mount } from '@vue/test-utils';
import * as z from 'zod';

const updateDraftValue = vi.fn();
vi.mock('@/bcap/util.ts', () => ({
    updateDraftValue: (...args: unknown[]) => updateDraftValue(...args),
}));

const isComplete = vi.fn();
vi.mock('@/bcap/validation.ts', () => ({
    buildTileValidation: () => ({ resolver: 'RESOLVER', isComplete }),
}));

import { useDraftStep } from './useDraftStep';

// Mount the composable inside a component so inject() resolves the provided refs.
function setup(draftId: unknown, draftData: unknown) {
    const captured: { value?: ReturnType<typeof useDraftStep> } = {};
    const emit = vi.fn();
    const Child = defineComponent({
        setup() {
            captured.value = useDraftStep(
                'investigation',
                z.object({}),
                'overview',
                emit,
            );
            return () => h('div');
        },
    });
    mount(Child, {
        global: {
            provide: { draftId: ref(draftId), draftData: ref(draftData) },
        },
    });
    return { step: captured.value!, emit };
}

beforeEach(() => {
    updateDraftValue.mockReset();
    isComplete.mockReset();
});

describe('useDraftStep', () => {
    it('exposes the resolver and injected draft data', () => {
        const data = { overview: { aliased_data: {} } };
        const { step } = setup('draft-1', data);
        expect(step.resolver).toBe('RESOLVER');
        expect(step.draftData?.value).toEqual(data);
    });

    it('isValid checks completeness of the validation tile', () => {
        isComplete.mockReturnValue(true);
        const tile = { foo: 'bar' };
        const { step } = setup('draft-1', { overview: { aliased_data: tile } });
        expect(step.isValid()).toBe(true);
        expect(isComplete).toHaveBeenCalledWith(tile);
    });

    it('updateValue writes the draft then emits the validity', () => {
        isComplete.mockReturnValue(false);
        const { step, emit } = setup('draft-7', { overview: {} });
        step.updateValue({ node_value: 1 } as never, 'attr', 'group');
        expect(updateDraftValue).toHaveBeenCalledWith(
            { overview: {} },
            'draft-7',
            'investigation',
            { node_value: 1 },
            'attr',
            'group',
        );
        expect(emit).toHaveBeenCalledWith('update:step-is-valid', false);
    });
});
