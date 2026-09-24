import { routeNames } from '@/bcap/apps/Permit/routes.ts';
import type { Crumb } from '@/bcap/apps/Permit/components/common/PermitBreadcrumbs.vue';
import type { QueryParam } from '@/bcap/types.ts';

// Crumbs back to a permit's Project Summary. No permit on the URL means the page
// was opened standalone, so it shows no crumbs at all.
export const permitCrumbs = (
    permitId: QueryParam,
    current: string,
    summaryRoute: string = routeNames.permitDetails,
): Crumb[] => {
    if (!permitId) return [];
    return [
        {
            label: 'Project Summary',
            to: {
                name: summaryRoute,
                params: { id: String(permitId) },
            },
        },
        { label: current },
    ];
};
