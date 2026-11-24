import arches from 'arches';
import type { RouteNamesType } from '@/bcgov_arches_common/routes.ts';

// Generates an external (submissions/) and internal (internal-permit-dashboard/)
// route pair for the same component. The internal name is derived by capitalising
// the first letter of the external name and prepending "internal".
const dualRoute = (
    slug: string,
    name: string,
    component: () => Promise<unknown>,
) => [
    {
        path: arches.urls.plugin(`submissions/${slug}`),
        name,
        component,
        meta: { shouldShowNavigation: true },
    },
    {
        path: arches.urls.plugin(`internal-permit-dashboard/${slug}`),
        name: `internal${name.charAt(0).toUpperCase()}${name.slice(1)}`,
        component,
        meta: { requiresInternal: true },
    },
];

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
    ...dualRoute(
        'permit/:id',
        'permitDetails',
        () =>
            import('@/bcap/apps/Permit/components/filing-summary/PermitDetails.vue'),
    ),
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
    ...dualRoute(
        'hcaPermitApplication/permitInfo',
        'hcaPermitInfo',
        () =>
            import('@/bcap/apps/Permit/Modules/HcaPermitApplicationModule/PermitInfo/PermitInfo.vue'),
    ),
    ...dualRoute(
        'hcaPermitApplication/methods',
        'hcaPermitMethods',
        () =>
            import('@/bcap/apps/Permit/Modules/HcaPermitApplicationModule/ArchMethods/ArchMethods.vue'),
    ),
    ...dualRoute(
        'hcaPermitApplication/personnel',
        'hcaPermitPersonnel',
        () =>
            import('@/bcap/apps/Permit/Modules/HcaPermitApplicationModule/SiteOversight/SiteOversight.vue'),
    ),
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
    internalPermitDetails: string;
    checklist: string;
    editchecklist: string;
    moduleReview: string;
    alterationsModule: string;
    baseModule: string;
    hcaPermitInfo: string;
    internalHcaPermitInfo: string;
    hcaPermitMethods: string;
    internalHcaPermitMethods: string;
    hcaPermitPersonnel: string;
    internalHcaPermitPersonnel: string;
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
    internalPermitDetails: 'internalPermitDetails',
    checklist: 'Checklist',
    editchecklist: 'EditChecklist',
    moduleReview: 'moduleReview',
    alterationsModule: 'alterationsModule',
    baseModule: 'baseModule',
    hcaPermitInfo: 'hcaPermitInfo',
    internalHcaPermitInfo: 'internalHcaPermitInfo',
    hcaPermitMethods: 'hcaPermitMethods',
    internalHcaPermitMethods: 'internalHcaPermitMethods',
    hcaPermitPersonnel: 'hcaPermitPersonnel',
    internalHcaPermitPersonnel: 'internalHcaPermitPersonnel',
    collectionModule: 'collectionModule',
    inspectionModule: 'inspectionModule',
    investigationModule: 'investigationModule',
    methodsModule: 'methodsModule',
    recordingsModule: 'recordingsModule',
    documentSubmission: 'documentSubmission',
};

export { routes, routeNames };
export type { ExternalPermitRouteNamesType };
