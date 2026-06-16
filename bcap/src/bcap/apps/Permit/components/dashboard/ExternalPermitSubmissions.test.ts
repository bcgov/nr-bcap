import { describe, it, expect, vi } from 'vitest';
import { shallowMount } from '@vue/test-utils';

vi.mock('arches', () => ({
    default: { urls: { plugin: (slug: string) => `/plugins/${slug}` } },
}));

import ExternalPermitSubmissions from './ExternalPermitSubmissions.vue';

describe('ExternalPermitSubmissions', () => {
    it('renders the workflow panel', () => {
        const wrapper = shallowMount(ExternalPermitSubmissions);
        expect(wrapper.html()).toBeTruthy();
    });
});
