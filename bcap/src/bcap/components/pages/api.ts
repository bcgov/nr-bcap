import arches from 'arches';
import { apiFetchJson } from '@/bcap/api.ts';
import type {
    ArchaeologicalSite,
    SiteVisit,
    PaginatedSiteVisitList,
} from '@/bcap/client/types.gen.ts';
import type { HriaDiscontinuedData } from '@/bcap/client/types.gen.ts';

export const getResourceData = async (
    graph_slug: string,
    resource_id: string,
): Promise<ArchaeologicalSite | SiteVisit | HriaDiscontinuedData> =>
    apiFetchJson(arches.urls.api_resource(graph_slug, resource_id));

export const getResourceList = async (
    graph_slug: string,
    resource_ids: string[],
): Promise<ArchaeologicalSite | SiteVisit | HriaDiscontinuedData> => {
    const url: URL = new URL(
        arches.urls.api_resource_list(graph_slug),
        window.location.origin,
    );
    url.searchParams.append('resource_ids', resource_ids.join(','));
    return apiFetchJson(url.toString());
};

export const getRelatedResourceData = async (
    graph_slug: string,
    resource_id: string,
): Promise<SiteVisit[] | HriaDiscontinuedData[]> => {
    const parsed = await apiFetchJson<PaginatedSiteVisitList>(
        arches.urls.api_site_related_resources(graph_slug, resource_id),
    );
    return parsed.results;
};
