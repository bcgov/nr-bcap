import arches from 'arches';
import type { RouteNamesType } from '@/bcgov_arches_common/routes.ts';

// No route declares that it needs a login: the profile endpoint the guard calls
// returns 403 for anyone not signed in, so every route is authenticated whether
// it asks or not. requiresInternal narrows a route to ministry staff on top.
const routes = [
    {
        path: arches.urls.plugin('submissions'),
        name: 'root',
        component: () =>
            import('@/bcap/apps/Permit/components/dashboard/SubmissionsDashboard.vue'),
        meta: {
            shouldShowNavigation: true,
        },
    },
    {
        path: arches.urls.plugin('internal-permit-dashboard'),
        name: 'internal-root',
        component: () =>
            import('@/bcap/apps/Permit/components/dashboard/InternalDashboard.vue'),
        meta: {
            requiresInternal: true,
        },
    },
    {
        path: arches.urls.plugin('submissions/permit/:id'),
        name: 'permitDetails',
        component: () =>
            import('@/bcap/apps/Permit/components/filing-summary/PermitDetails.vue'),
        meta: {
            shouldShowNavigation: true,
        },
    },
    {
        path: arches.urls.plugin('submissions/moduleReview'),
        name: 'moduleReview',
        component: () =>
            import('@/bcap/apps/Permit/components/filing-summary/ModuleSubmissionReview.vue'),
        meta: {
            shouldShowNavigation: true,
        },
    },
    {
        path: arches.urls.plugin('submissions/alterationsModule'),
        name: 'alterationsModule',
        component: () =>
            import('@/bcap/apps/Permit/Modules/AlterationsModule/AlterationsModule.vue'),
        meta: {
            shouldShowNavigation: true,
        },
    },
    {
        path: arches.urls.plugin('submissions/baseModule'),
        name: 'baseModule',
        component: () =>
            import('@/bcap/apps/Permit/Modules/BaseModule/BaseModule.vue'),
        meta: {
            shouldShowNavigation: true,
        },
    },
    {
        path: arches.urls.plugin('submissions/collectionModule'),
        name: 'collectionModule',
        component: () =>
            import('@/bcap/apps/Permit/Modules/CollectionsModule/CollectionsModule.vue'),
        meta: {
            shouldShowNavigation: true,
        },
    },
    {
        path: arches.urls.plugin('submissions/inspectionModule'),
        name: 'inspectionModule',
        component: () =>
            import('@/bcap/apps/Permit/Modules/InspectionModule/InspectionModule.vue'),
        meta: {
            shouldShowNavigation: true,
        },
    },
    {
        path: arches.urls.plugin('submissions/investigationModule'),
        name: 'investigationModule',
        component: () =>
            import('@/bcap/apps/Permit/Modules/InvestigationModule/InvestigationModule.vue'),
        meta: {
            shouldShowNavigation: true,
        },
    },
    {
        path: arches.urls.plugin('submissions/methodsModule'),
        name: 'methodsModule',
        component: () =>
            import('@/bcap/apps/Permit/Modules/MethodsModule/MethodsModule.vue'),
        meta: {
            shouldShowNavigation: true,
        },
    },
    {
        path: arches.urls.plugin('submissions/recordingsModule'),
        name: 'recordingsModule',
        component: () =>
            import('@/bcap/apps/Permit/Modules/RecordingsModule/RecordingsModule.vue'),
        meta: {
            shouldShowNavigation: true,
        },
    },
    {
        path: arches.urls.plugin('submissions/documentSubmission'),
        name: 'documentSubmission',
        component: () =>
            import('@/bcap/apps/Permit/Modules/DocumentSubmissionModule/DocumentSubmissionModule.vue'),
        meta: {
            shouldShowNavigation: true,
        },
    },
    {
        path: arches.urls.plugin('internal-permit-dashboard/checklist'),
        name: 'Checklist',
        component: () =>
            import('@/bcap/apps/Permit/components/checklist/TaskChecklist.vue'),
        meta: {
            requiresInternal: true,
        },
    },
    {
        path: arches.urls.plugin('internal-permit-dashboard/EditChecklist'),
        name: 'EditChecklist',
        component: () =>
            import('@/bcap/apps/Permit/components/checklist/EditChecklist.vue'),
        meta: {
            requiresInternal: true,
        },
    },
];

type ExternalPermitRouteNamesType = RouteNamesType & {
    home: string;
    permitDetails: string;
    checklist: string;
    editchecklist: string;
    moduleReview: string;
    alterationsModule: string;
    baseModule: string;
    collectionModule: string;
    inspectionModule: string;
    investigationModule: string;
    methodsModule: string;
    recordingsModule: string;
    documentSubmission: string;
};

const routeNames: ExternalPermitRouteNamesType = {
    home: 'root',
    login: '',
    permitDetails: 'permitDetails',
    checklist: 'Checklist',
    editchecklist: 'EditChecklist',
    moduleReview: 'moduleReview',
    alterationsModule: 'alterationsModule',
    baseModule: 'baseModule',
    collectionModule: 'collectionModule',
    inspectionModule: 'inspectionModule',
    investigationModule: 'investigationModule',
    methodsModule: 'methodsModule',
    recordingsModule: 'recordingsModule',
    documentSubmission: 'documentSubmission',
};

export { routes, routeNames };
export type { ExternalPermitRouteNamesType };
