import arches from 'arches';
import type { RouteNamesType } from '@/bcgov_arches_common/routes.ts';
const routes = [
    {
        path: arches.urls.plugin('external-permit-workflows'),
        name: 'root',
        component: () =>
            import('@/bcap/apps/Permit/components/dashboard/ExternalPermitSubmissions.vue'),
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: true,
        },
    },
    {
        path: arches.urls.plugin('external-permit-workflows/submit'),
        name: 'newPermit',
        component: () =>
            import('@/bcap/apps/Permit/SubmitApplication/SubmitApplication.vue'),
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: true,
        },
    },
];

type ExternalPermitRouteNamesType = RouteNamesType & {
    home: string;
    newPermit: string;
};

const routeNames: ExternalPermitRouteNamesType = {
    home: 'root',
    newPermit: 'newPermit',
    login: '',
    // updateSite: 'updateSite',
    // editSite: 'editSite',
    // search: "search",
    // advancedSearch: "advanced-search",
    // schemes: "schemes",
    // concept: "concept",
    // scheme: "scheme",
};
export { routes, routeNames };
export type { ExternalPermitRouteNamesType };
