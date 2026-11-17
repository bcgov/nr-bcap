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

    it('renders an html field with HTML tags stripped', () => {
        const wrapper = shallowMount(ReviewSummary, {
            props: {
                fields: [
                    {
                        label: 'Description',
                        type: 'html' as const,
                        value: '<p>Hello <strong>world</strong></p>',
                    },
                ],
            },
        });
        expect(wrapper.text()).toContain('Hello world');
        expect(wrapper.text()).not.toContain('<p>');
    });

    it('renders a text field with its raw value', () => {
        const wrapper = shallowMount(ReviewSummary, {
            props: {
                fields: [{ label: 'Site Name', value: 'Eagle Creek Site' }],
            },
        });
        expect(wrapper.text()).toContain('Eagle Creek Site');
    });

    it('hides a non-map field when the value is empty', () => {
        const wrapper = shallowMount(ReviewSummary, {
            props: {
                fields: [{ label: 'Hidden Field', value: '' }],
            },
        });
        expect(wrapper.text()).not.toContain('Hidden Field');
    });
});
