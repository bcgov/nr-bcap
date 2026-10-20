import { routes, routeNames } from './routes';

describe('Permit routes', () => {
    it('defines a route for each Permit screen', () => {
        const byName = Object.fromEntries(routes.map((r) => [r.name, r]));

        expect(routes).toHaveLength(15);
        expect(Object.keys(byName).sort()).toEqual([
            'Checklist',
            'EditChecklist',
            'alterationsModule',
            'baseModule',
            'collectionModule',
            'documentSubmission',
            'inspectionModule',
            'internal-root',
            'internalPermitDetails',
            'investigationModule',
            'methodsModule',
            'moduleReview',
            'permitDetails',
            'recordingsModule',
            'root',
        ]);
    });

    it('builds each path from the matching plugin slug', () => {
        const byName = Object.fromEntries(routes.map((r) => [r.name, r]));

        expect(byName['root'].path).toBe('/plugins/submissions');
        expect(byName['internal-root'].path).toBe(
            '/plugins/internal-permit-dashboard',
        );
        expect(byName['baseModule'].path).toBe(
            '/plugins/submissions/baseModule',
        );
        expect(byName['Checklist'].path).toBe(
            '/plugins/internal-permit-dashboard/checklist',
        );
        expect(byName['EditChecklist'].path).toBe(
            '/plugins/internal-permit-dashboard/EditChecklist',
        );
    });

    it('lazy-loads every route component', () => {
        for (const route of routes) {
            expect(typeof route.component).toBe('function');
        }
    });

    it('marks the externally-facing routes nav-visible', () => {
        const byName = Object.fromEntries(routes.map((r) => [r.name, r]));

        expect(byName['root'].meta).toEqual({ shouldShowNavigation: true });
        expect(byName['baseModule'].meta).toEqual({
            shouldShowNavigation: true,
        });
    });

    it('restricts the internal dashboard and its checklists to staff', () => {
        const byName = Object.fromEntries(routes.map((r) => [r.name, r]));
        const staffOnly = routes
            .filter((route) => route.meta?.requiresInternal)
            .map((route) => route.name)
            .sort();

        expect(staffOnly).toEqual([
            'Checklist',
            'EditChecklist',
            'internal-root',
            'internalPermitDetails',
        ]);
        expect(byName['root'].meta?.requiresInternal).toBeUndefined();
    });

    it('maps friendly route-name aliases to the registered names', () => {
        expect(routeNames.home).toBe('root');
        expect(routeNames.baseModule).toBe('baseModule');
        expect(routeNames.checklist).toBe('Checklist');
        expect(routeNames.editchecklist).toBe('EditChecklist');
        expect(routeNames.login).toBe('');
    });
});
