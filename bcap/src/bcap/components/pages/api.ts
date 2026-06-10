import arches from 'arches';
import { z } from 'zod';
import { apiDashboardInternalRetrieveResponse } from '@/bcap/client/zod/internal-dashboard.zod.ts';
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
        arches.urls.api_resource(graph_slug, resource_id),
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
): Promise<PermitRequirementSchema> => {
    const response = await fetch(
        arches.urls.api_process_requirements(resource_id),
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
        arches.urls.api_requirement_submission(resource_id),
    );
    if (!response.ok) {
        const text = await response.text();
        throw new Error(text || response.statusText);
    }

    return await response.json();
};

// Card shape from the generated Zod response schema (one item of `results`).
export type InternalDashboardCard = NonNullable<
    z.infer<typeof apiDashboardInternalRetrieveResponse>['results']
>[number];

export const getInternalDashboardData = async (
    showUnassigned: boolean = false,
    page: number = 1,
    limit: number = 100,
): Promise<InternalDashboardCard[]> => {
    try {
        // Will need to update to all
        const apiUrl = `${arches.urls.dashboard}?limit=${limit}&page=${page}${showUnassigned ? '&status=UNASSIGNED' : ''}`;
        const response = await fetch(apiUrl);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = apiDashboardInternalRetrieveResponse.safeParse(
            await response.json(),
        );
        if (!result.success) {
            console.error(
                'Dashboard response failed validation:',
                result.error,
            );
            return [];
        }

        return result.data.results ?? [];
    } catch (error) {
        console.error('Error fetching projects from backend:', error);
        return [];
    }
};
