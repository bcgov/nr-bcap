import { describe, it, expect, vi } from 'vitest';
import { mount } from '@vue/test-utils';

vi.mock(
    '@/bcgov_arches_common/components/SimpleMap/SimpleMap.vue',
    async () => {
        const { defineComponent } = await import('vue');
        return {
            default: defineComponent({
                name: 'MapStub',
                props: {
                    graphSlug: { type: String, default: undefined },
                    nodeAlias: { type: String, default: undefined },
                    mode: { type: String, default: undefined },
                    aliasedNodeData: { type: Object, default: undefined },
                    useUtmCoords: { type: Boolean, default: false },
                },
                template: '<div data-testid="map-stub"></div>',
            }),
        };
    },
);

vi.mock('@/arches_component_lab/widgets/constants.ts', () => ({
    VIEW: 'view',
}));

import DetailsSection1 from './DetailsSection1.vue';

describe('DetailsSection1', () => {
    it('passes use-utm-coords=true to the Map component', () => {
        const wrapper = mount(DetailsSection1, {
            props: { data: undefined },
            global: {
                stubs: {
                    DetailsSection: true,
                    EmptyState: true,
                },
            },
        });

        const map = wrapper.findComponent({ name: 'MapStub' });
        expect(map.exists()).toBe(true);
        expect(map.props('useUtmCoords')).toBe(true);
    });
});
