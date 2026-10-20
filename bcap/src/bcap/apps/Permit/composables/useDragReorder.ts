import { reactive } from 'vue';

// Drag-to-reorder within a keyed group. Callers pass a group key so independent
// lists (e.g. each module's own requirements) can't drag across each other.
// Dropping reorders the passed list in place, then runs the persist callback.
export function useDragReorder() {
    const drag = reactive({
        key: null as string | null,
        from: null as number | null,
        over: null as number | null,
    });

    const start = (key: string, index: number) => {
        drag.key = key;
        drag.from = index;
    };

    const enter = (key: string, index: number) => {
        if (drag.from !== null && drag.key === key) drag.over = index;
    };

    const end = () => {
        drag.key = null;
        drag.from = null;
        drag.over = null;
    };

    const drop = async <T>(
        key: string,
        index: number,
        list: T[],
        persist: () => void | Promise<void>,
    ) => {
        const from = drag.from;
        const sameGroup = drag.key === key;
        end();
        if (from === null || !sameGroup || from === index) return;
        const [moved] = list.splice(from, 1);
        list.splice(index, 0, moved);
        await persist();
    };

    // True when the given item is the one being dragged in its group.
    const isDragging = (key: string, index: number) =>
        drag.key === key && drag.from === index;

    // True when the given item is the current drop target (and not the source).
    const isOver = (key: string, index: number) =>
        drag.key === key && drag.over === index && drag.from !== index;

    return { drag, start, enter, end, drop, isDragging, isOver };
}
