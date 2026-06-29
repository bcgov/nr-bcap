import type { ArchesDraftData } from '@/bcap/types.ts';
import { getCsrfToken } from '@/bcap/util.ts';

// Thin fetch wrapper: attaches JSON + CSRF headers, serializes the body, and
// throws on a non-2xx response. CSRF on safe methods is harmless (Django ignores it).
export const apiFetch = async (
    url: string,
    options: { method?: string; body?: unknown } = {},
): Promise<Response> => {
    const { method = 'GET', body } = options;
    const headers: Record<string, string> = {
        Accept: 'application/json',
        'X-CSRFToken': getCsrfToken(),
    };
    if (body !== undefined) headers['Content-Type'] = 'application/json';

    const response = await fetch(url, {
        method,
        headers,
        ...(body !== undefined && { body: JSON.stringify(body) }),
    });

    if (!response.ok) {
        const detail = await response.text().catch(() => response.statusText);
        throw new Error(
            `${method} ${url} failed (${response.status}): ${detail}`,
        );
    }
    return response;
};

export const saveDraftFieldToBackend = async (
    draftId: string,
    graphSlug: string,
    fullDraftData: ArchesDraftData,
) => {
    try {
        const patchUrl = `/bcap/api/resource_draft/${graphSlug}/${draftId}`;

        await apiFetch(patchUrl, {
            method: 'PATCH',
            body: { data: fullDraftData },
        });

        console.log('Successfully auto-saved full draft data.');
    } catch (error) {
        console.error('Failed to auto-save draft data:', error);
    }
};
