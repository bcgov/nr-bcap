import { getCsrfToken } from '@/bcap/util.ts';

export enum HttpMethod {
    Get = 'GET',
    Post = 'POST',
    Patch = 'PATCH',
    Put = 'PUT',
    Delete = 'DELETE',
}

interface ApiFetchOptions {
    method?: HttpMethod;
    body?: unknown;
}

export const TRY_AGAIN =
    'Please try again, or contact support if it keeps happening.';

export const UNEXPECTED_ERROR = `Something went wrong on our end. ${TRY_AGAIN}`;

// An error whose message is written for the user, so it may be shown as is.
export class UserFacingError extends Error {
    name = 'UserFacingError';
}

export class ApiError extends UserFacingError {
    name = 'ApiError';
    status: number;

    constructor(message: string, status: number) {
        super(message);
        this.status = status;
    }
}

// DRF errors come in varied shapes: { detail }, { field: [msgs] }, nested
// { new_contributor: { email: [msg] } }, or a bare list.
export const flattenMessages = (value: unknown): string[] => {
    if (typeof value === 'string') return [value];
    if (Array.isArray(value)) return value.flatMap(flattenMessages);
    if (value && typeof value === 'object') {
        return Object.values(value).flatMap(flattenMessages);
    }
    return [];
};

const fallbackMessage = (status: number): string => {
    if (status === 403) return "You don't have access to do that.";
    if (status === 404) return 'That item could not be found.';
    if (status >= 500) return UNEXPECTED_ERROR;
    return 'The request could not be completed.';
};

// Anything but a JSON error body (a debug page, a proxy's HTML) is never shown.
const readableError = async (response: Response): Promise<string> => {
    const text = await response.text().catch(() => '');
    try {
        // A tile save repeats its missing-values message under every field.
        const messages = [...new Set(flattenMessages(JSON.parse(text)))];
        // One message per line; the error box and toast keep the breaks.
        if (messages.length) return messages.join('\n');
    } catch {
        // Not JSON (an HTML error page or empty body) is expected, so nothing is
        // logged: the failed request is already logged above, and the network
        // tab shows the body better. The status-based message below takes over.
    }
    return fallbackMessage(response.status);
};

// Thin fetch wrapper: attaches JSON + CSRF headers, serializes the body, and
// throws an ApiError on a non-2xx response. CSRF on safe methods is harmless
// (Django ignores it).
export const apiFetch = async (
    url: string,
    options: ApiFetchOptions = {},
): Promise<Response> => {
    const { method = HttpMethod.Get, body } = options;
    const isForm = body instanceof FormData;
    const headers: Record<string, string> = {
        Accept: 'application/json',
        'X-CSRFToken': getCsrfToken(),
    };
    if (body !== undefined && !isForm)
        headers['Content-Type'] = 'application/json';

    const response = await fetch(url, {
        method,
        headers,
        ...(body !== undefined && {
            body: isForm ? (body as FormData) : JSON.stringify(body),
        }),
    });

    if (!response.ok) {
        console.error(`${method} ${url} failed (${response.status})`);
        throw new ApiError(await readableError(response), response.status);
    }
    return response;
};

// apiFetch, then parse the body as T. Use for endpoints that return JSON so the
// caller gets a typed value instead of casting response.json(). The 204/no-body
// endpoints keep calling apiFetch directly.
export const apiFetchJson = async <T>(
    url: string,
    options: ApiFetchOptions = {},
): Promise<T> => {
    const response = await apiFetch(url, options);
    return (await response.json()) as T;
};
