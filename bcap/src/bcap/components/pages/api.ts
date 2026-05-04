import type { ArchaeologySiteSchema } from '@/bcap/schema/ArchaeologySiteSchema.ts';
import type {
    SiteVisitResponse,
    SiteVisitSchema,
} from '@/bcap/schema/SiteVisitSchema.ts';
import type { HriaDiscontinuedDataSchema } from '@/bcap/schema/HriaDiscontinuedDataSchema.ts';
import type { PermitRequirementSchema } from '@/bcap/schema/PermitRequirementSchema.ts';
import type { RequirementSubmissionSchema } from '@/bcap/schema/RequirementSubmissionSchema.ts';

export const getResourceData = async (
    graph_slug: string,
    resource_id: string,
): Promise<
    ArchaeologySiteSchema | SiteVisitSchema | HriaDiscontinuedDataSchema
> => {
    const response = await fetch(
        `/bcap/api/resource/${graph_slug}/${resource_id}`,
    );
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
        `/bcap/api/arch_site_related_resources/${graph_slug}/${resource_id}`,
    );
    if (!response.ok) {
        const text = await response.text();
        throw new Error(text || response.statusText);
    }
    const parsed: SiteVisitResponse = await response.json();
    return parsed.results;
};

export const getPermitRequirementData = async (
    resource_id: string,
): Promise<PermitRequirementSchema> => {
    const response = await fetch(
        `/bcap/api/permit_requirements/${resource_id}/`,
    );
    if (!response.ok) {
        const text = await response.text();
        throw new Error(text || response.statusText);
    }

    return await response.json();
};

export const getRequirementSubmissionData = async (
    resource_id: string,
): Promise<RequirementSubmissionSchema> => {
    const response = await fetch(
        `/bcap/api/requirement_submissions/${resource_id}/`,
    );
    if (!response.ok) {
        const text = await response.text();
        throw new Error(text || response.statusText);
    }

    return await response.json();
};
