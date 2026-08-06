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
    formatError?: (response: Response) => Promise<string>;
}

// Thin fetch wrapper: attaches JSON + CSRF headers, serializes the body, and
// throws on a non-2xx response. CSRF on safe methods is harmless (Django ignores it).
export const apiFetch = async (
    url: string,
    options: ApiFetchOptions = {},
): Promise<Response> => {
    const { method = HttpMethod.Get, body, formatError } = options;
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
        if (formatError) throw new Error(await formatError(response));
        const detail = await response.text().catch(() => response.statusText);
        throw new Error(
            `${method} ${url} failed (${response.status}): ${detail}`,
        );
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
