import arches from 'arches';
import { apiFetchJson, HttpMethod } from '@/bcap/api.ts';
import type {
    ContributorSummary,
    RegistrationLinkRequest,
    RegistrationLinkResponse,
} from '@/bcap/client/types.gen.ts';

// DRF errors come in varied shapes -- { detail }, { field: [msgs] }, nested
// { new_contributor: { email: [msg] } }, or a bare list. Collect the leaf
// strings so the user sees readable text instead of raw JSON.
const flattenMessages = (value: unknown): string[] => {
    if (typeof value === 'string') return [value];
    if (Array.isArray(value)) return value.flatMap(flattenMessages);
    if (value && typeof value === 'object') {
        return Object.values(value).flatMap(flattenMessages);
    }
    return [];
};

const errorMessage = async (response: Response): Promise<string> => {
    const text = await response.text();
    try {
        const messages = flattenMessages(JSON.parse(text));
        return messages.join(' ') || text || response.statusText;
    } catch {
        return text || response.statusText;
    }
};

export const getUnlinkedContributors = async (
    search?: string,
): Promise<ContributorSummary[]> => {
    const query = search ? `?search=${encodeURIComponent(search)}` : '';
    return apiFetchJson(`${arches.urls.unlinked_contributors}${query}`, {
        formatError: errorMessage,
    });
};

export const getAssignableGroups = async (): Promise<string[]> =>
    apiFetchJson(arches.urls.assignable_groups, { formatError: errorMessage });

export const issueRegistrationLink = async (
    body: RegistrationLinkRequest,
): Promise<RegistrationLinkResponse> =>
    apiFetchJson(arches.urls.registration_link, {
        method: HttpMethod.Post,
        body,
        formatError: errorMessage,
    });
