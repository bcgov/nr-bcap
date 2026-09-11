import { UserFacingError } from '@/bcap/api.ts';
import {
    DEFAULT_ERROR_TOAST_LIFE,
    ERROR,
} from '@/bcgov_arches_common/constants.ts';

import type { App } from 'vue';
import type { ToastServiceMethods } from 'primevue/toastservice';

// Module level so stores and api helpers can report errors, not just components.
let toast: ToastServiceMethods | undefined;
let lastShown = { key: '', at: 0 };

export const userMessage = (error: unknown): string | undefined =>
    error instanceof UserFacingError ? error.message : undefined;

export const notifyError = (summary: string, error?: unknown): void => {
    console.error(`${summary}:`, error);
    if (!toast) return;
    const detail = userMessage(error);
    const key = `${summary}|${detail}`;
    const now = Date.now();
    // Autosave retries would otherwise stack identical toasts.
    if (key === lastShown.key && now - lastShown.at < DEFAULT_ERROR_TOAST_LIFE)
        return;
    lastShown = { key, at: now };
    toast.add({
        severity: ERROR,
        life: DEFAULT_ERROR_TOAST_LIFE,
        summary,
        detail,
    });
};

export const installErrorHandling = (app: App): void => {
    const { $toast, $gettext } = app.config.globalProperties;
    toast = $toast;
    const summary = $gettext ? $gettext('Something went wrong.') : 'Something went wrong.';
    app.config.errorHandler = (error) => notifyError(summary, error);
    // Only our own errors: arches' knockout code leaves rejections too.
    window.addEventListener('unhandledrejection', (event) => {
        if (event.reason instanceof UserFacingError)
            notifyError(summary, event.reason);
    });
};
