import { reactive } from 'vue';

// Confirm-then-run flow for a destructive action: opening records the target and
// shows the dialog, confirming runs the action and closes it.
export function useConfirmAction<T>(action: (target: T) => Promise<void>) {
    const state = reactive({
        visible: false,
        busy: false,
        target: null as T | null,
    });

    const open = (target: T) => {
        state.target = target as T;
        state.visible = true;
    };

    const confirm = async () => {
        if (state.target === null) return;
        state.busy = true;
        try {
            await action(state.target as T);
            state.visible = false;
        } catch (error) {
            console.error('Confirm action failed:', error);
        } finally {
            state.busy = false;
        }
    };

    return { state, open, confirm };
}
