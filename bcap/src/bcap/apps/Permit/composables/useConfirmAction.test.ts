const notifyError = vi.fn();
vi.mock('@/bcap/notify.ts', () => ({
    notifyError: (...args: unknown[]) => notifyError(...args),
}));

import { useConfirmAction } from './useConfirmAction';

beforeEach(() => {
    notifyError.mockReset();
});

describe('useConfirmAction', () => {
    it('starts hidden with no target', () => {
        const { state } = useConfirmAction(async () => {});
        expect(state.visible).toBe(false);
        expect(state.busy).toBe(false);
        expect(state.target).toBeNull();
    });

    it('open records the target and shows the dialog', () => {
        const { state, open } = useConfirmAction<{ id: string }>(
            async () => {},
        );
        open({ id: 'x' });
        expect(state.visible).toBe(true);
        expect(state.target).toEqual({ id: 'x' });
    });

    it('confirm runs the action with the target then closes', async () => {
        const action = vi.fn().mockResolvedValue(undefined);
        const { state, open, confirm } = useConfirmAction<string>(action);
        open('target-1');

        await confirm();

        expect(action).toHaveBeenCalledWith('target-1');
        expect(state.visible).toBe(false);
        expect(state.busy).toBe(false);
    });

    it('does nothing when confirm is called with no target', async () => {
        const action = vi.fn();
        const { confirm } = useConfirmAction(action);
        await confirm();
        expect(action).not.toHaveBeenCalled();
    });

    it('sets busy while the action is in flight and clears it after', async () => {
        let resolve: () => void = () => {};
        const action = vi.fn(
            () =>
                new Promise<void>((r) => {
                    resolve = r;
                }),
        );
        const { state, open, confirm } = useConfirmAction<string>(action);
        open('t');

        const pending = confirm();
        expect(state.busy).toBe(true);

        resolve();
        await pending;
        expect(state.busy).toBe(false);
    });

    it('keeps the dialog open and clears busy when the action rejects', async () => {
        const error = new Error('boom');
        const action = vi.fn().mockRejectedValue(error);
        const { state, open, confirm } = useConfirmAction<string>(action);
        open('t');

        await confirm();

        // A failed action leaves the dialog open so the user can retry.
        expect(state.visible).toBe(true);
        expect(state.busy).toBe(false);
        expect(notifyError).toHaveBeenCalledWith(
            'That action could not be completed',
            error,
        );
    });

    it('does not report anything when the action succeeds', async () => {
        const { open, confirm } = useConfirmAction<string>(async () => {});
        open('t');
        await confirm();
        expect(notifyError).not.toHaveBeenCalled();
    });
});
