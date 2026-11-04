import arches from 'arches';
import { apiFetchJson, HttpMethod } from '@/bcap/api.ts';
import type {
    ContributorSummary,
    RegistrationLinkRequest,
    RegistrationLinkResponse,
} from '@/bcap/client/types.gen.ts';

export const getUnlinkedContributors = async (
    search?: string,
): Promise<ContributorSummary[]> => {
    const query = search ? `?search=${encodeURIComponent(search)}` : '';
    return apiFetchJson(`${arches.urls.unlinked_contributors}${query}`);
};

export const getAssignableGroups = async (): Promise<string[]> =>
    apiFetchJson(arches.urls.assignable_groups);

export const issueRegistrationLink = async (
    body: RegistrationLinkRequest,
): Promise<RegistrationLinkResponse> =>
    apiFetchJson(arches.urls.registration_link, {
        method: HttpMethod.Post,
        body,
    });
