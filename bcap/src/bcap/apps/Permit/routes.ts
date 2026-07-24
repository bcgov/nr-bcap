import arches from 'arches';
import type { RouteNamesType } from '@/bcgov_arches_common/routes.ts';
const routes = [
    {
        path: arches.urls.plugin('submissions'),
        name: 'root',
        component: () =>
            import('@/bcap/apps/Permit/components/dashboard/SubmissionsDashboard.vue'),
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
        path: arches.urls.plugin('submissions/permit/:id'),
        name: 'permitDetails',
        component: () =>
            import('@/bcap/apps/Permit/components/filing-summary/PermitDetails.vue'),
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: true,
        },
    },
    {
        path: arches.urls.plugin('submissions/alterationsModule'),
        name: 'alterationsModule',
        component: () =>
            import('@/bcap/apps/Permit/Modules/AlterationsModule/AlterationsModule.vue'),
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: true,
        },
    },
    {
        path: arches.urls.plugin('submissions/baseModule'),
        name: 'baseModule',
        component: () =>
            import('@/bcap/apps/Permit/Modules/BaseModule/BaseModule.vue'),
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: true,
        },
    },
    {
        path: arches.urls.plugin('submissions/collectionModule'),
        name: 'collectionModule',
        component: () =>
            import('@/bcap/apps/Permit/Modules/CollectionsModule/CollectionsModule.vue'),
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: true,
        },
    },
    {
        path: arches.urls.plugin('submissions/inspectionModule'),
        name: 'inspectionModule',
        component: () =>
            import('@/bcap/apps/Permit/Modules/InspectionModule/InspectionModule.vue'),
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: true,
        },
    },
    {
        path: arches.urls.plugin('submissions/investigationModule'),
        name: 'investigationModule',
        component: () =>
            import('@/bcap/apps/Permit/Modules/InvestigationModule/InvestigationModule.vue'),
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: true,
        },
    },
    {
        path: arches.urls.plugin('submissions/methodsModule'),
        name: 'methodsModule',
        component: () =>
            import('@/bcap/apps/Permit/Modules/MethodsModule/MethodsModule.vue'),
        meta: {
            shouldShowNavigation: true,
            requiresAuthentication: true,
        },
    },
    {
        path: arches.urls.plugin('submissions/recordingsModule'),
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
            import('@/bcap/apps/Permit/components/checklist/TaskChecklist.vue'),
    },
    {
        path: arches.urls.plugin('internal-permit-dashboard/EditChecklist'),
        name: 'EditChecklist',
        component: () =>
            import('@/bcap/apps/Permit/components/checklist/EditChecklist.vue'),
    },
];

type ExternalPermitRouteNamesType = RouteNamesType & {
    home: string;
    permitDetails: string;
    checklist: string;
    editchecklist: string;
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
    editchecklist: 'EditChecklist',
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
