import type { App } from 'vue';

const fakeApp = (
    add: ReturnType<typeof vi.fn>,
    remove: ReturnType<typeof vi.fn> = vi.fn(),
) =>
    ({
        config: { globalProperties: { $toast: { add, remove } } },
    }) as unknown as App;

describe('notifyError', () => {
    let notify: typeof import('./notify');
    let ApiError: typeof import('./api').ApiError;

    beforeEach(async () => {
        vi.resetModules();
        vi.spyOn(console, 'error').mockImplementation(() => {});
        notify = await import('./notify');
        ({ ApiError } = await import('./api'));
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('only logs when no app has a toast host', () => {
        notify.notifyError('Save failed', new Error('x'));
        expect(console.error).toHaveBeenCalled();
    });

    it("shows an ApiError's message as the detail", () => {
        const add = vi.fn();
        notify.installErrorHandling(fakeApp(add));
        notify.notifyError(
            'Save failed',
            new ApiError('Name is required.', 400),
        );
        expect(add).toHaveBeenCalledWith(
            expect.objectContaining({
                summary: 'Save failed',
                detail: 'Name is required.',
            }),
        );
    });

    it('shows a UserFacingError thrown by our own code', async () => {
        const { UserFacingError } = await import('./api');
        const add = vi.fn();
        notify.installErrorHandling(fakeApp(add));
        notify.notifyError(
            'Submission failed',
            new UserFacingError('No draft.'),
        );
        expect(add.mock.calls[0][0].detail).toBe('No draft.');
    });

    it('keeps any other error out of the toast', () => {
        const add = vi.fn();
        notify.installErrorHandling(fakeApp(add));
        notify.notifyError('Save failed', new TypeError('x is undefined'));
        expect(add.mock.calls[0][0].detail).toBeUndefined();
    });

    it('replaces the same toast rather than stacking it', () => {
        const add = vi.fn();
        const remove = vi.fn();
        notify.installErrorHandling(fakeApp(add, remove));
        const error = new ApiError('Offline.', 503);
        notify.notifyError('Autosave failed', error);
        notify.notifyError('Autosave failed', error);
        expect(remove).toHaveBeenCalledWith(add.mock.calls[0][0]);
        expect(add).toHaveBeenCalledTimes(2);
    });

    it('reports errors Vue catches', () => {
        const add = vi.fn();
        const app = fakeApp(add);
        notify.installErrorHandling(app);
        app.config.errorHandler?.(new Error('boom'), null, '');
        expect(add).toHaveBeenCalledWith(
            expect.objectContaining({ summary: 'Something went wrong.' }),
        );
    });
});
