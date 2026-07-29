import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useDraftStore } from '@/bcap/stores/draft.ts';
import { createDraft } from '@/bcap/apps/Permit/api.ts';
import { saveDraftFieldToBackend } from '@/bcap/api.ts';

vi.mock('@/bcap/apps/Permit/api.ts', () => ({ createDraft: vi.fn() }));
vi.mock('@/bcap/api.ts', () => ({ saveDraftFieldToBackend: vi.fn() }));

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
