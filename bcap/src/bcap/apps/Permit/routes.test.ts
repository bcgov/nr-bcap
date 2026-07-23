import { describe, it, expect, vi } from 'vitest';

vi.mock('arches', () => ({
    default: {
        urls: {
            plugin: (slug: string) => `/plugins/${slug}`,
        },
    },
}));

import { routes, routeNames } from './routes';

describe('Permit routes', () => {
    it('defines a route for each Permit screen', () => {
        const byName = Object.fromEntries(routes.map((r) => [r.name, r]));

        expect(routes).toHaveLength(12);
        expect(Object.keys(byName).sort()).toEqual([
            'Checklist',
            'EditChecklist',
            'alterationsModule',
            'baseModule',
            'collectionModule',
            'inspectionModule',
            'internal-root',
            'investigationModule',
            'methodsModule',
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

    it('marks the externally-facing routes as auth-required and nav-visible', () => {
        const byName = Object.fromEntries(routes.map((r) => [r.name, r]));

        expect(byName['root'].meta).toEqual({
            shouldShowNavigation: true,
            requiresAuthentication: true,
        });
        expect(byName['baseModule'].meta).toEqual({
            shouldShowNavigation: true,
            requiresAuthentication: true,
        });
        // Internal dashboard routes carry no nav/auth meta.
        expect(byName['internal-root'].meta).toBeUndefined();
        expect(byName['Checklist'].meta).toBeUndefined();
    });

    it('maps friendly route-name aliases to the registered names', () => {
        expect(routeNames.home).toBe('root');
        expect(routeNames.baseModule).toBe('baseModule');
        expect(routeNames.checklist).toBe('Checklist');
        expect(routeNames.editchecklist).toBe('EditChecklist');
        expect(routeNames.login).toBe('');
    });
});
