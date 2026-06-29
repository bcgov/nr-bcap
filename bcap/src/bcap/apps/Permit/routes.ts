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
        path: arches.urls.plugin('internal-permit-dashboard'),
        name: 'internal-root',
        component: () =>
            import('@/bcap/apps/Permit/components/dashboard/InternalDashboard.vue'),
    },
    {
        path: arches.urls.plugin('external-permit-workflows/permit/:id'),
        name: 'permitDetails',
        component: () =>
            import('@/bcap/apps/Permit/components/dashboard/PermitDetails.vue'),
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: true,
        },
    },
    {
        path: arches.urls.plugin('external-permit-workflows/alterationsModule'),
        name: 'alterationsModule',
        component: () =>
            import('@/bcap/apps/Permit/Modules/AlterationsModule/AlterationsModule.vue'),
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: true,
        },
    },
    {
        path: arches.urls.plugin('external-permit-workflows/baseModule'),
        name: 'baseModule',
        component: () =>
            import('@/bcap/apps/Permit/Modules/BaseModule/BaseModule.vue'),
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: true,
        },
    },
    {
        path: arches.urls.plugin('external-permit-workflows/collectionModule'),
        name: 'collectionModule',
        component: () =>
            import('@/bcap/apps/Permit/Modules/CollectionsModule/CollectionsModule.vue'),
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: true,
        },
    },
    {
        path: arches.urls.plugin('external-permit-workflows/inspectionModule'),
        name: 'inspectionModule',
        component: () =>
            import('@/bcap/apps/Permit/Modules/InspectionModule/InspectionModule.vue'),
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: true,
        },
    },
    {
        path: arches.urls.plugin(
            'external-permit-workflows/investigationModule',
        ),
        name: 'investigationModule',
        component: () =>
            import('@/bcap/apps/Permit/Modules/InvestigationModule/InvestigationModule.vue'),
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: true,
        },
    },
    {
        path: arches.urls.plugin('external-permit-workflows/methodsModule'),
        name: 'methodsModule',
        component: () =>
            import('@/bcap/apps/Permit/Modules/MethodsModule/MethodsModule.vue'),
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: true,
        },
    },
    {
        path: arches.urls.plugin('external-permit-workflows/recordingsModule'),
        name: 'recordingsModule',
        component: () =>
            import('@/bcap/apps/Permit/Modules/RecordingsModule/RecordingsModule.vue'),
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: true,
        },
    },
    {
        path: arches.urls.plugin('internal-permit-dashboard/checklist'),
        name: 'Checklist',
        component: () =>
            import('@/bcap/apps/Permit/components/dashboard/TaskChecklist.vue'),
    },
    {
        path: arches.urls.plugin('internal-permit-dashboard/CreateChecklist'),
        name: 'CreateChecklist',
        component: () =>
            import('@/bcap/apps/Permit/components/dashboard/CreateChecklist.vue'),
    },
];

type ExternalPermitRouteNamesType = RouteNamesType & {
    home: string;
    permitDetails: string;
    checklist: string;
    createchecklist: string;
    alterationsModule: string;
    baseModule: string;
    collectionModule: string;
    inspectionModule: string;
    investigationModule: string;
    methodsModule: string;
    recordingsModule: string;
};

const routeNames: ExternalPermitRouteNamesType = {
    home: 'root',
    login: '',
    permitDetails: 'permitDetails',
    checklist: 'Checklist',
    createchecklist: 'CreateChecklist',
    alterationsModule: 'alterationsModule',
    baseModule: 'baseModule',
    collectionModule: 'collectionModule',
    inspectionModule: 'inspectionModule',
    investigationModule: 'investigationModule',
    methodsModule: 'methodsModule',
    recordingsModule: 'recordingsModule',
};
export { routes, routeNames };
export type { ExternalPermitRouteNamesType };
