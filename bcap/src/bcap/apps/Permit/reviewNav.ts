import type { PermitHeader } from '@/bcap/apps/Permit/components/filing-summary/PermitHeaderBand.vue';

export interface ReviewNav {
    graph: string;
    resourceId: string;
    permitId: string;
    title: string;
    permitHeader?: PermitHeader;
}

// Handoff for the submission review page. Set right before navigating; the page
// reads it on mount. A refresh loses it, which the page treats as "reopen it".
let pending: ReviewNav | null = null;

export const setReviewNav = (nav: ReviewNav) => {
    pending = nav;
};

export const getReviewNav = (): ReviewNav | null => pending;
