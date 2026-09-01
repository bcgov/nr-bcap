import { mount } from '@vue/test-utils';

vi.mock(
    '@/bcgov_arches_common/widgets/SimpleMapWidget/SimpleMapWidget.vue',
    async () => {
        const { defineComponent } = await import('vue');
        return {
            default: defineComponent({
                name: 'MapStub',
                props: {
                    graphSlug: { type: String, default: '' },
                    nodeAlias: { type: String, default: '' },
                    mode: { type: String, default: '' },
                    aliasedNodeData: { type: Object, default: undefined },
                    useUtmCoords: { type: Boolean, default: false },
                },
                template: '<div data-testid="map-stub"></div>',
            }),
        };
    },
);

vi.mock('@/arches_vue_components/widgets/constants.ts', () => ({
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
