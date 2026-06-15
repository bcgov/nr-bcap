import { describe, it, expect, vi } from 'vitest';

vi.mock('arches', () => ({
    default: {
        urls: {
            plugin: (slug: string) => `/plugins/${slug}`,
        },
    },
}));

import { routes, routeNames } from './routes';

describe('Admin routes', () => {
    it('defines the invite-contributor route', () => {
        expect(routes).toHaveLength(1);
        expect(routes[0].name).toBe('invite-contributor');
    });

    it('builds the path from the plugin slug', () => {
        expect(routes[0].path).toBe('/plugins/contributor-invitations');
    });

    it('lazy-loads the route component', () => {
        expect(typeof routes[0].component).toBe('function');
    });

    it('maps the home alias to the registered name and leaves login blank', () => {
        expect(routeNames.home).toBe('invite-contributor');
        expect(routeNames.login).toBe('');
    });
});
