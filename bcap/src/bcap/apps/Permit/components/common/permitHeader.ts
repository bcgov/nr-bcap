import { fetchPermitDetails } from '@/bcap/apps/Permit/api.ts';
import type { PermitHeader } from '@/bcap/apps/Permit/components/filing-summary/PermitHeaderBand.vue';
import type { PermitAliasedData } from '@/bcap/types.ts';

// The header band's fields, read off a permit's aliased data. Shared so the
// pages that open in their own tab (submission review, checklists) show the
// same band as the permit view.
export const permitHeaderFrom = (aliased: PermitAliasedData): PermitHeader => {
    const appIdent = aliased.application_identification?.aliased_data;
    const devDetails =
        aliased.proposed_project?.aliased_data?.development_project_details
            ?.aliased_data;
    const appAdmin = aliased.application_admin;

    return {
        projectName: appIdent?.project_name?.display_value || 'Unnamed Project',
        applicationNumber: appIdent?.application_id?.display_value || 'Pending',
        submissionType: appIdent?.filing_type?.display_value || '',
        // Left empty when unset so the header can mute it rather than stating a
        // sector that was never given.
        sector: devDetails?.industrial_sector?.display_value || '',
        submittedDate:
            appAdmin?.aliased_data?.application_submission_date
                ?.display_value || null,
    };
};

export const loadPermitHeader = async (
    permitId: unknown,
): Promise<PermitHeader | null> => {
    if (!permitId) return null;
    try {
        const aliased = await fetchPermitDetails(String(permitId));
        return aliased ? permitHeaderFrom(aliased) : null;
    } catch (error) {
        console.error('Failed to load permit header:', error);
        return null;
    }
};
