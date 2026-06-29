import arches from 'arches';
import { z } from 'zod';
import {
    zApiDashboardInternalRetrieveQuery,
    zContributorOption,
    zInternalDashboardCard,
    zInternalDashboardPage,
    zNewContributor,
    zProcessRequirement,
    zRegistrationLinkRequest,
    zRegistrationLinkResponse,
} from '@/bcap/client/zod.gen.ts';
import type { ArchaeologySiteSchema } from '@/bcap/schema/ArchaeologySiteSchema.ts';
import type {
    SiteVisitResponse,
    SiteVisitSchema,
} from '@/bcap/schema/SiteVisitSchema.ts';
import type { HriaDiscontinuedDataSchema } from '@/bcap/schema/HriaDiscontinuedDataSchema.ts';

export type ProcessRequirement = z.infer<typeof zProcessRequirement>;

export const getResourceData = async (
    graph_slug: string,
    resource_id: string,
): Promise<
    ArchaeologySiteSchema | SiteVisitSchema | HriaDiscontinuedDataSchema
> => {
    const response = await fetch(
        arches.urls.api_resource(graph_slug, resource_id),
    );
    if (!response.ok) {
        const text = await response.text();
        throw new Error(text || response.statusText);
    }
    return await response.json();
};

export const getResourceList = async (
    graph_slug: string,
    resource_ids: string[],
): Promise<
    ArchaeologySiteSchema | SiteVisitSchema | HriaDiscontinuedDataSchema
> => {
    const url: URL = new URL(
        arches.urls.api_resource_list(graph_slug),
        window.location.origin,
    );
    url.searchParams.append('resource_ids', resource_ids.join(','));
    const response = await fetch(url);
    if (!response.ok) {
        const text = await response.text();
        throw new Error(text || response.statusText);
    }
    return await response.json();
};

export const getRelatedResourceData = async (
    graph_slug: string,
    resource_id: string,
): Promise<SiteVisitSchema[] | HriaDiscontinuedDataSchema[]> => {
    const response = await fetch(
        arches.urls.api_site_related_resources(graph_slug, resource_id),
    );
    if (!response.ok) {
        const text = await response.text();
        throw new Error(text || response.statusText);
    }
    const parsed: SiteVisitResponse = await response.json();
    return parsed.results;
};

export const getProcessRequirementData = async (
    resource_id: string,
): Promise<ProcessRequirement> => {
    const response = await fetch(
        arches.urls.api_process_requirements(resource_id),
    );
    if (!response.ok) {
        const text = await response.text();
        throw new Error(text || response.statusText);
    }

    const json = await response.json();
    const result = zProcessRequirement.safeParse(json);
    if (!result.success) {
        console.warn('ProcessRequirement failed validation:', result.error);
        return json as ProcessRequirement;
    }
    return result.data;
};

export type UnlinkedContributor = z.infer<typeof zContributorOption>;
export type NewContributorInput = z.infer<typeof zNewContributor>;
export type RegistrationLinkResult = z.infer<typeof zRegistrationLinkResponse>;
export type IssueRegistrationLinkBody = z.infer<
    typeof zRegistrationLinkRequest
>;

const csrfToken = (): string =>
    document.cookie
        .split('; ')
        .find((row) => row.startsWith('csrftoken='))
        ?.split('=')[1] || '';

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
): Promise<UnlinkedContributor[]> => {
    const query = search ? `?search=${encodeURIComponent(search)}` : '';
    const response = await fetch(
        `${arches.urls.unlinked_contributors}${query}`,
    );
    if (!response.ok) {
        throw new Error(await errorMessage(response));
    }
    return await response.json();
};

export const getAssignableGroups = async (): Promise<string[]> => {
    const response = await fetch(arches.urls.assignable_groups);
    if (!response.ok) {
        throw new Error(await errorMessage(response));
    }
    return await response.json();
};

export const issueRegistrationLink = async (
    body: IssueRegistrationLinkBody,
): Promise<RegistrationLinkResult> => {
    const response = await fetch(arches.urls.registration_link, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken(),
        },
        body: JSON.stringify(body),
    });
    if (!response.ok) {
        throw new Error(await errorMessage(response));
    }
    return await response.json();
};

export type DashboardStatus = z.infer<
    typeof zApiDashboardInternalRetrieveQuery
>['status'];

export type InternalDashboardCard = z.infer<typeof zInternalDashboardCard>;

export const getInternalDashboardData = async (
    status?: DashboardStatus,
    page: number = 1,
    limit: number = 100,
): Promise<InternalDashboardCard[]> => {
    try {
        // no status means all results -- omit the param entirely
        const statusParam = status ? `&status=${status}` : '';
        const apiUrl = `${arches.urls.dashboard}?limit=${limit}&page=${page}${statusParam}`;
        const response = await fetch(apiUrl);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = zInternalDashboardPage.parse(await response.json());
        return data.results ?? [];
    } catch (error) {
        console.error('Error fetching projects from backend:', error);
        return [];
    }
};
