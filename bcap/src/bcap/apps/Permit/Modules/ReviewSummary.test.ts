import { shallowMount } from '@vue/test-utils';
import ReviewSummary from './ReviewSummary.vue';

vi.mock(
    '@/arches_vue_components/generics/GenericWidget/GenericWidget.vue',
    () => ({ default: { name: 'GenericWidget', template: '<div />' } }),
);
vi.mock('@/bcgov_arches_common/composables/useMapFrameAutoCentre.ts', () => ({
    useMapFrameAutoCentre: vi.fn(),
}));

const boundary = (nodeValue: unknown) => [
    {
        label: 'Project Boundary',
        value: { node_value: nodeValue, display_value: '' },
        type: 'map' as const,
    },
];

describe('ReviewSummary.vue', () => {
    it.each([
        ['no value', undefined],
        ['a null node value', null],
        ['an empty collection', { type: 'FeatureCollection', features: [] }],
    ])('says no geometry was uploaded for %s', (_, nodeValue) => {
        const wrapper = shallowMount(ReviewSummary, {
            props: { fields: boundary(nodeValue) },
        });
        expect(wrapper.text()).toContain('No geometry has been uploaded');
        expect(wrapper.findComponent({ name: 'GenericWidget' }).exists()).toBe(
            false,
        );
    });

    it('shows the map when there is a feature', () => {
        const wrapper = shallowMount(ReviewSummary, {
            props: {
                fields: boundary({
                    type: 'FeatureCollection',
                    features: [{ type: 'Feature', geometry: null }],
                }),
            },
        });
        expect(wrapper.text()).not.toContain('No geometry has been uploaded');
        expect(wrapper.findComponent({ name: 'GenericWidget' }).exists()).toBe(
            true,
        );
    });
});
