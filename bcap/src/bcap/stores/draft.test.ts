import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useDraftStore } from '@/bcap/stores/draft.ts';
import {
    createDraft,
    saveDraftFieldToBackend,
} from '@/bcap/apps/Permit/api.ts';

vi.mock('@/bcap/apps/Permit/api.ts', () => ({
    createDraft: vi.fn(),
    saveDraftFieldToBackend: vi.fn(),
}));

const value = { node_value: 'x', display_value: 'x' } as never;

describe('draft store saveNow', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.useFakeTimers();
        vi.mocked(createDraft).mockResolvedValue({ id: 'new-1' } as never);
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('writes the current data immediately and cancels the pending autosave', async () => {
        const store = useDraftStore();
        store.initDraft('investigation');
        store.loadDraft('draft-7', {});
        store.updateValue(value, 'field', 'group');

        await store.saveNow();

        expect(saveDraftFieldToBackend).toHaveBeenCalledWith(
            'draft-7',
            'investigation',
            store.draftData,
            '',
        );
        // The debounce would otherwise fire a second, redundant save.
        await vi.advanceTimersByTimeAsync(2000);
        expect(saveDraftFieldToBackend).toHaveBeenCalledTimes(1);
    });

    it('creates the draft first when the form has edits but no id yet', async () => {
        const store = useDraftStore();
        store.initDraft('investigation', 'permit-1');
        store.updateValue(value, 'field', 'group');

        await store.saveNow();

        expect(createDraft).toHaveBeenCalledWith('investigation', 'permit-1');
        expect(store.draftId).toBe('new-1');
        expect(saveDraftFieldToBackend).toHaveBeenCalledWith(
            'new-1',
            'investigation',
            store.draftData,
            '',
        );
    });

    it('saves the step the user moved to with the draft', async () => {
        const store = useDraftStore();
        store.initDraft('investigation');
        store.loadDraft('draft-7', {});
        store.setCurrentStep('Contacts');

        await store.saveNow();

        expect(saveDraftFieldToBackend).toHaveBeenCalledWith(
            'draft-7',
            'investigation',
            store.draftData,
            'Contacts',
        );
    });

    it('leaves no empty draft behind when nothing was edited', async () => {
        const store = useDraftStore();
        store.initDraft('investigation', 'permit-1');

        await store.saveNow();

        expect(createDraft).not.toHaveBeenCalled();
        expect(saveDraftFieldToBackend).not.toHaveBeenCalled();
    });
});

describe('draft store step tracking', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.useFakeTimers();
        vi.mocked(createDraft).mockResolvedValue({ id: 'new-1' } as never);
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('records the step without saving before a draft exists', async () => {
        const store = useDraftStore();
        store.initDraft('investigation');

        store.setCurrentStep('Contacts');

        expect(store.currentStep).toBe('Contacts');
        // No draft id yet, so nothing is created just by navigating steps.
        await vi.advanceTimersByTimeAsync(2000);
        expect(createDraft).not.toHaveBeenCalled();
        expect(saveDraftFieldToBackend).not.toHaveBeenCalled();
    });

    it('clears the step when a new filing starts', () => {
        const store = useDraftStore();
        store.loadDraft('draft-7', { x: 1 } as never, 'Contacts');
        expect(store.currentStep).toBe('Contacts');

        store.initDraft('investigation', 'permit-1');

        expect(store.currentStep).toBe('');
        expect(store.draftId).toBeNull();
        expect(store.draftData).toEqual({});
        expect(store.parentPermitId).toBe('permit-1');
    });

    it('takes the step from the draft it loads', () => {
        const store = useDraftStore();
        store.initDraft('investigation');

        store.loadDraft('draft-7', {}, 'Details');

        expect(store.currentStep).toBe('Details');
    });
});
