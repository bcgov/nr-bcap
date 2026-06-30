import { beforeAll, beforeEach, vi } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';

beforeAll(() => {
    // routes.ts (and others) call arches.urls.<name>(...) at import time, so the
    // stub needs a urls object. The Proxy returns a path-building function for any
    // url name, so tests that only transitively import these modules don't crash.
    vi.mock('arches', () => ({
        default: {
            urls: new Proxy(
                {},
                {
                    get:
                        () =>
                        (...args: string[]) =>
                            '/' + args.join('/'),
                },
            ),
        },
    }));

    vi.mock('vue3-gettext', () => ({
        useGettext: () => ({
            $gettext: (text: string) => (text)
        })
    }));
});

// Fresh Pinia per test so stores start empty and never leak state across tests.
// Components that call useStore() without an installed plugin fall back to this
// active instance, so mounts work without per-test setup.
beforeEach(() => {
    setActivePinia(createPinia());
});
