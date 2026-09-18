import { TRY_AGAIN, UserFacingError } from '@/bcap/api.ts';
import { ERROR } from '@/bcgov_arches_common/constants.ts';

import type { App } from 'vue';
import type { ToastMessageOptions } from 'primevue/toast';
import type { ToastServiceMethods } from 'primevue/toastservice';

const ERROR_TOAST_LIFE = 20000;

// Module level so stores and api helpers can report errors, not just components.
let toast: ToastServiceMethods | undefined;
let lastShown: { key: string; message: ToastMessageOptions } | undefined;

export const userMessage = (error: unknown): string | undefined =>
    error instanceof UserFacingError ? error.message : undefined;

export type InlineErrorData = { title: string; detail: string };

// The detail line for an error a page shows itself: what the server said, or the
// generic retry when it said nothing usable. The surrounding slot titles it, so
// this never repeats the context. Api failures are already logged by the fetch
// wrapper, so only anything else (a bug) is logged here.
export const inlineMessage = (error: unknown): string => {
    const message = userMessage(error);
    if (message === undefined) console.error(error);
    return message ?? TRY_AGAIN;
};

export const notifyError = (summary: string, error?: unknown): void => {
    console.error(`${summary}:`, error);
    if (!toast) return;
    const detail = userMessage(error);
    const key = `${summary}|${detail}`;
    // Autosave retries would otherwise stack identical toasts; removing one the
    // user already closed is a no-op.
    if (lastShown?.key === key) toast.remove(lastShown.message);
    const message = {
        severity: ERROR,
        life: ERROR_TOAST_LIFE,
        summary,
        detail,
    };
    toast.add(message);
    lastShown = { key, message };
};

export const installErrorHandling = (app: App): void => {
    const { $toast, $gettext } = app.config.globalProperties;
    toast = $toast;
    const summary = $gettext
        ? $gettext('Something went wrong.')
        : 'Something went wrong.';
    app.config.errorHandler = (error) => notifyError(summary, error);
    // Only our own errors: arches' knockout code leaves rejections too.
    window.addEventListener('unhandledrejection', (event) => {
        if (event.reason instanceof UserFacingError)
            notifyError(summary, event.reason);
    });
};
