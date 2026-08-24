import arches from 'arches';
import { apiFetchJson } from '@/bcap/api.ts';
import type { ArchaeologySiteSchema } from '@/bcap/schema/ArchaeologySiteSchema.ts';
import type {
    SiteVisitResponse,
    SiteVisitSchema,
} from '@/bcap/schema/SiteVisitSchema.ts';
import type { HriaDiscontinuedDataSchema } from '@/bcap/schema/HriaDiscontinuedDataSchema.ts';

const rawError = async (response: Response): Promise<string> =>
    (await response.text()) || response.statusText;

export const getResourceData = async (
    graph_slug: string,
    resource_id: string,
): Promise<
    ArchaeologySiteSchema | SiteVisitSchema | HriaDiscontinuedDataSchema
> =>
    apiFetchJson(arches.urls.api_resource(graph_slug, resource_id), {
        formatError: rawError,
    });

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
    return apiFetchJson(url.toString(), { formatError: rawError });
};

export const getRelatedResourceData = async (
    graph_slug: string,
    resource_id: string,
): Promise<SiteVisitSchema[] | HriaDiscontinuedDataSchema[]> => {
    const parsed = await apiFetchJson<SiteVisitResponse>(
        arches.urls.api_site_related_resources(graph_slug, resource_id),
        { formatError: rawError },
    );
    return parsed.results;
};
