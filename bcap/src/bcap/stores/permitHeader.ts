import { reactive } from 'vue';
import { defineStore } from 'pinia';
import { fetchPermitDetails } from '@/bcap/apps/Permit/api.ts';
import type { PermitHeader } from '@/bcap/apps/Permit/components/filing-summary/PermitHeaderBand.vue';
import type { PermitAliasedData } from '@/bcap/types.ts';

const headerFrom = (aliased: PermitAliasedData): PermitHeader => {
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

// What the submission review page opens: set right before navigating to it. A
// refresh empties the store, which that page treats as "reopen it".
export interface ReviewTarget {
    graph: string;
    resourceId: string;
    permitId: string;
    title: string;
}

// The permit currently being viewed: its header band and the submission the user
// drilled into. Held here rather than passed down, so the pages that show the
// band (permit view, submission review, checklists) render it without refetching
// on every navigation.
export const usePermitHeaderStore = defineStore('bcapPermitHeader', () => {
    const state = reactive({
        permitId: '',
        header: null as PermitHeader | null,
        review: null as ReviewTarget | null,
    });

    function setReview(target: ReviewTarget) {
        state.review = target;
    }

    // The permit view already has the aliased data, so it sets the band rather
    // than making the other pages fetch it again.
    function setFromAliased(permitId: string, aliased: PermitAliasedData) {
        state.permitId = permitId;
        state.header = headerFrom(aliased);
        return state.header;
    }

    // A page opened in its own tab starts with an empty store, so it loads.
    async function load(permitId: string): Promise<PermitHeader | null> {
        if (!permitId || state.permitId === permitId) return state.header;
        try {
            const aliased = await fetchPermitDetails(permitId);
            if (aliased) setFromAliased(permitId, aliased);
        } catch (error) {
            console.error('Failed to load permit header:', error);
        }
        return state.header;
    }

    return { state, setReview, setFromAliased, load };
});
