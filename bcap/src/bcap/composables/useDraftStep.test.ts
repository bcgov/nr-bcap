import * as z from 'zod';

const isComplete = vi.fn();
vi.mock('@/bcap/validation.ts', () => ({
    buildTileValidation: () => ({ resolver: 'RESOLVER', isComplete }),
}));

import { useDraftStep } from './useDraftStep';
import { useDraftStore } from '@/bcap/stores/draft.ts';

beforeEach(() => {
    isComplete.mockReset();
});

describe('useDraftStep', () => {
    it('exposes the resolver and the store draft data', () => {
        const store = useDraftStore();
        store.draftData = { overview: { aliased_data: {} } };
        const step = useDraftStep(z.object({}), 'overview');
        expect(step.resolver).toBe('RESOLVER');
        expect(step.draftData.value).toEqual({
            overview: { aliased_data: {} },
        });
    });

    it('isValid checks completeness of the validation tile', () => {
        isComplete.mockReturnValue(true);
        const store = useDraftStore();
        const tile = { foo: 'bar' };
        store.draftData = { overview: { aliased_data: tile } };
        const step = useDraftStep(z.object({}), 'overview');
        expect(step.isValid()).toBe(true);
        expect(isComplete).toHaveBeenCalledWith(tile);
    });

    it('isValid is true when no schema is given', () => {
        const step = useDraftStep();
        expect(step.isValid()).toBe(true);
    });

    it('updateValue writes through the store then emits validity', () => {
        isComplete.mockReturnValue(false);
        const store = useDraftStore();
        const spy = vi.spyOn(store, 'updateValue').mockImplementation(() => {});
        const emit = vi.fn();
        const step = useDraftStep(z.object({}), 'overview', emit);
        step.updateValue({ node_value: 1 } as never, 'attr', 'group');
        expect(spy).toHaveBeenCalledWith({ node_value: 1 }, 'attr', 'group');
        expect(emit).toHaveBeenCalledWith('update:step-is-valid', false);
    });
});
