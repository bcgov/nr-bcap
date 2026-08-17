import { mount } from '@vue/test-utils';

import PermitBreadcrumbs from './PermitBreadcrumbs.vue';
import { permitCrumbs } from './permitCrumbs.ts';

const stubs = {
    RouterLink: {
        props: ['to'],
        template: '<a :href="JSON.stringify(to)"><slot /></a>',
    },
};

const mountCrumbs = (crumbs: unknown[]) =>
    mount(PermitBreadcrumbs, { props: { crumbs }, global: { stubs } });

describe('PermitBreadcrumbs', () => {
    it('links every crumb but the last', () => {
        const wrapper = mountCrumbs([
            { label: 'Project Summary', to: { name: 'PermitDetails' } },
            { label: 'Recommend Referral', to: { name: 'Checklist' } },
        ]);

        expect(wrapper.findAll('a')).toHaveLength(1);
        expect(wrapper.find('a').text()).toBe('Project Summary');
        expect(wrapper.find('.crumb-current').text()).toBe(
            'Recommend Referral',
        );
    });

    it('separates crumbs but never leads with one', () => {
        const wrapper = mountCrumbs([
            { label: 'Project Summary', to: { name: 'PermitDetails' } },
            { label: 'Checklist' },
        ]);
        expect(wrapper.findAll('.crumb-sep')).toHaveLength(1);
    });
});

describe('permitCrumbs', () => {
    it('returns nothing without a permit, so a standalone page shows no trail', () => {
        expect(permitCrumbs(undefined, 'true', 'Checklist')).toEqual([]);
    });

    it('keeps ?staff on the return trip', () => {
        const [summary] = permitCrumbs('permit-1', 'true', 'Checklist');
        expect(summary.to).toMatchObject({
            params: { id: 'permit-1' },
            query: { staff: 'true' },
        });
    });

    it('drops the staff query for an external view', () => {
        const [summary] = permitCrumbs('permit-1', undefined, 'Checklist');
        expect(summary.to).toMatchObject({ query: {} });
    });
});
