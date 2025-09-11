import type { ArchaeologySiteSchema } from "@/bcap/schema/ArchaeologySiteSchema.ts";
import type {
    SiteVisitResponse,
    SiteVisitSchema,
} from "@/bcap/schema/SiteVisitSchema.ts";
import type { HriaDiscontinuedDataSchema } from "@/bcap/schema/HriaDiscontinuedDataSchema.ts";

export const getResourceData = async (
    graph_slug: string,
    resource_id: string,
): Promise<ArchaeologySiteSchema | SiteVisitSchema> => {
    const response = await fetch(
        `/bcap/api/resource/${graph_slug}/${resource_id}`,
    ).then();
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};

type ErrorResponse = Record<string, string>;
export const getRelatedResourceData = async (
    graph_slug: string,
    resource_id: string,
): Promise<SiteVisitSchema[] | HriaDiscontinuedDataSchema[]> => {
    const response = await fetch(
        `/bcap/api/arch_site_related_resources/${graph_slug}/${resource_id}`,
    ).then();
    const parsed: SiteVisitResponse | ErrorResponse = await response.json();
    if (!response.ok)
        throw new Error(
            Object.values(parsed as ErrorResponse).join(",") ||
                response.statusText,
        );
    return (parsed as SiteVisitResponse).results;
};
