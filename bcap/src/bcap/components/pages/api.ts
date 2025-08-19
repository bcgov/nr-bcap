import type { ArchaeologySiteSchema } from "@/bcap/schema/ArchaeologySiteSchema.ts";

export const getResourceData = async (
    graph_slug: string,
    resource_id: string,
): Promise<ArchaeologySiteSchema> => {
    const response = await fetch(
        `/bcap/api/resource/${graph_slug}/${resource_id}`,
    ).then();
    const parsed = await response.json();
    if (!response.ok) throw new Error(parsed.message || response.statusText);
    return parsed;
};
