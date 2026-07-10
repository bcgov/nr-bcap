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

        expect(routes).toHaveLength(13);
        expect(Object.keys(byName).sort()).toEqual([
            'Checklist',
            'CreateChecklist',
            'alterationsModule',
            'baseModule',
            'collectionModule',
            'inspectionModule',
            'internal-root',
            'investigationModule',
            'messageDemo',
            'methodsModule',
            'permitDetails',
            'recordingsModule',
            'root',
        ]);
    });

    it('builds each path from the matching plugin slug', () => {
        const byName = Object.fromEntries(routes.map((r) => [r.name, r]));

        expect(byName['root'].path).toBe('/plugins/external-permit-workflows');
        expect(byName['internal-root'].path).toBe(
            '/plugins/internal-permit-dashboard',
        );
        expect(byName['baseModule'].path).toBe(
            '/plugins/external-permit-workflows/baseModule',
        );
        expect(byName['Checklist'].path).toBe(
            '/plugins/internal-permit-dashboard/checklist',
        );
        expect(byName['CreateChecklist'].path).toBe(
            '/plugins/internal-permit-dashboard/CreateChecklist',
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
        expect(routeNames.createchecklist).toBe('CreateChecklist');
        expect(routeNames.login).toBe('');
    });
});
