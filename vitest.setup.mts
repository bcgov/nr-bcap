import { beforeAll, beforeEach, vi } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { config, RouterLinkStub } from '@vue/test-utils';

// silencing the warning everywhere.
config.global.stubs.RouterLink = RouterLinkStub;

// The url names tests assert on, at the paths Django really serves them from,
// so an expected url in a test reads like the one in the browser. Anything not
// listed falls through to the Proxy below.
const urls: Record<string, unknown> = {
    api_process_requirements: (id: string) =>
        `/bcap/api/process_requirement/${id}`,
    api_resource: (graphSlug: string, id: string) =>
        `/bcap/api/resource/${graphSlug}/${id}`,
    api_resource_blank: (graphSlug: string) =>
        `/bcap/api/resource/${graphSlug}/blank`,
    api_site_related_resources: (graphSlug: string, id: string) =>
        `/bcap/api/arch_site_related_resources/${graphSlug}/${id}`,
    api_workflow_draft: (graphSlug: string) =>
        `/bcap/api/workflow_draft/${graphSlug}`,
    api_workflow_draft_all: '/bcap/api/workflow_draft',
    assignable_contributors: '/bcap/api/contributors/assignable',
    assignable_groups: '/bcap/api/assignable_groups',
    bcap_message_detail: (messageId: string) =>
        `/bcap/api/bcap_message/${messageId}`,
    bcap_message_resource_threads: (resourceId: string) =>
        `/bcap/api/bcap_message/resource/${resourceId}/threads`,
    bcap_message_thread_messages: (threadId: string) =>
        `/bcap/api/bcap_message/thread/${threadId}`,
    dashboard: '/bcap/api/dashboard',
    dashboard_external: '/bcap/api/dashboard/external',
    module_requirement: (
        permitId: string,
        moduleTileId: string,
        requirementId: string,
    ) =>
        `/bcap/api/permit_application/${permitId}/module/${moduleTileId}/requirement/${requirementId}`,
    permit_application_create: '/bcap/api/permit_application',
    plugin: (slug: string) => `/plugins/${slug}`,
    registration_link: '/bcap/api/registration_link',
    seed_process_requirements: (permitId: string, permitType: string) =>
        `/bcap/api/permit_application/${permitId}/process_requirement/${permitType}`,
    unlinked_contributors: '/bcap/api/unlinked_contributors',
};

beforeAll(() => {
    // routes.ts (and others) call arches.urls.<name>(...) at import time, so the
    // stub needs a urls object. Unnamed urls fall back to a path built from the
    // arguments, so a module only transitively imported doesn't crash.
    vi.mock('arches', () => ({
        default: {
            urls: new Proxy(urls, {
                get: (target, name: string) =>
                    target[name] ??
                    ((...args: string[]) => '/' + args.join('/')),
            }),
        },
    }));

    vi.mock('vue3-gettext', () => ({
        useGettext: () => ({
            $gettext: (text: string) => (text)
        })
    }));

    // The real GenericWidget needs an active pinia and a live
    // card_x_node_x_widget fetch. Drive the stub with `.vm.$emit(...)`:
    // `update:value` is the bare node_value, `update:aliasedNodeData` the node.
    vi.mock(
        '@/arches_vue_components/generics/GenericWidget/GenericWidget.vue',
        () => ({
            default: {
                name: 'GenericWidget',
                emits: ['update:value', 'update:aliasedNodeData'],
                template: '<div class="mock-widget" />',
            },
        }),
    );
});

// Fresh Pinia per test so stores start empty and never leak state across tests.
// Components that call useStore() without an installed plugin fall back to this
// active instance, so mounts work without per-test setup.
beforeEach(() => {
    setActivePinia(createPinia());
});
