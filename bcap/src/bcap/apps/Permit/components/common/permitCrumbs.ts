import { routeNames } from '@/bcap/apps/Permit/routes.ts';
import type { Crumb } from '@/bcap/apps/Permit/components/common/PermitBreadcrumbs.vue';

// Crumbs back to a permit's Project Summary, preserving ?staff so the return
// trip keeps the staff (or external) view. No permit on the URL means the page
// was opened standalone, so it shows no crumbs at all.
export const permitCrumbs = (
    permitId: unknown,
    staff: unknown,
    current: string,
): Crumb[] => {
    if (!permitId) return [];
    return [
        {
            label: 'Project Summary',
            to: {
                name: routeNames.permitDetails,
                params: { id: String(permitId) },
                query: staff ? { staff: String(staff) } : {},
            },
        },
        { label: current },
    ];
};
