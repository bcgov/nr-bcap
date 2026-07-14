import { describe, it, expect, vi } from 'vitest';
import { useDragReorder } from './useDragReorder';

describe('useDragReorder', () => {
    it('reorders the list on a drop within the same group and persists', async () => {
        const persist = vi.fn();
        const list = ['a', 'b', 'c'];
        const { start, drop } = useDragReorder();

        start('g', 0);
        await drop('g', 2, list, persist);

        expect(list).toEqual(['b', 'c', 'a']);
        expect(persist).toHaveBeenCalledOnce();
    });

    it('does not reorder or persist when dropping onto the source index', async () => {
        const persist = vi.fn();
        const list = ['a', 'b', 'c'];
        const { start, drop } = useDragReorder();

        start('g', 1);
        await drop('g', 1, list, persist);

        expect(list).toEqual(['a', 'b', 'c']);
        expect(persist).not.toHaveBeenCalled();
    });

    it('ignores a drop that crosses into a different group', async () => {
        const persist = vi.fn();
        const list = ['a', 'b', 'c'];
        const { start, drop } = useDragReorder();

        start('groupA', 0);
        await drop('groupB', 2, list, persist);

        expect(list).toEqual(['a', 'b', 'c']);
        expect(persist).not.toHaveBeenCalled();
    });

    it('does nothing when no drag was started', async () => {
        const persist = vi.fn();
        const list = ['a', 'b'];
        const { drop } = useDragReorder();

        await drop('g', 0, list, persist);

        expect(list).toEqual(['a', 'b']);
        expect(persist).not.toHaveBeenCalled();
    });

    it('tracks the drop target only within the active group', () => {
        const { start, enter, drag } = useDragReorder();

        start('g', 0);
        enter('g', 2);
        expect(drag.over).toBe(2);

        // Entering an item in another group is ignored.
        enter('other', 1);
        expect(drag.over).toBe(2);
    });

    it('does not set an over target before a drag starts', () => {
        const { enter, drag } = useDragReorder();
        enter('g', 1);
        expect(drag.over).toBeNull();
    });

    it('end clears all drag state', () => {
        const { start, enter, end, drag } = useDragReorder();
        start('g', 0);
        enter('g', 1);

        end();

        expect(drag.key).toBeNull();
        expect(drag.from).toBeNull();
        expect(drag.over).toBeNull();
    });

    it('isDragging marks the source item in its group', () => {
        const { start, isDragging } = useDragReorder();
        start('g', 1);
        expect(isDragging('g', 1)).toBe(true);
        expect(isDragging('g', 0)).toBe(false);
        expect(isDragging('other', 1)).toBe(false);
    });

    it('isOver marks the drop target but never the source', () => {
        const { start, enter, isOver } = useDragReorder();
        start('g', 0);
        enter('g', 2);
        expect(isOver('g', 2)).toBe(true);
        expect(isOver('g', 0)).toBe(false);
    });

    it('clears the dragging state after a completed drop', async () => {
        const list = ['a', 'b', 'c'];
        const { start, drop, isDragging, drag } = useDragReorder();

        start('g', 0);
        await drop('g', 1, list, vi.fn());

        expect(drag.from).toBeNull();
        expect(isDragging('g', 0)).toBe(false);
    });
});
