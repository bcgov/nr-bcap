import arches from 'arches';
import type { RouteNamesType } from '@/bcgov_arches_common/routes.ts';

const routes = [
    {
        path: arches.urls.plugin('contributor-invitations'),
        name: 'invite-contributor',
        component: () =>
            import('@/bcap/apps/Admin/components/InviteContributor.vue'),
    },
];

type AdminRouteNamesType = RouteNamesType & {
    home: string;
};

const routeNames: AdminRouteNamesType = {
    home: 'invite-contributor',
    login: '',
};

export { routes, routeNames };
export type { AdminRouteNamesType };
