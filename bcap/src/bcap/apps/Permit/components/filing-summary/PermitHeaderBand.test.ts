import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import PermitHeaderBand, { type PermitHeader } from './PermitHeaderBand.vue';

const makeHeader = (overrides: Partial<PermitHeader> = {}): PermitHeader => ({
    projectName: 'Riverside Dig',
    applicationNumber: 'APP-42',
    submissionType: 'Permit Application - Standard',
    sector: 'Mining',
    submittedDate: '2026-07-23',
    ...overrides,
});

describe('PermitHeaderBand', () => {
    it('renders the project name', () => {
        const wrapper = mount(PermitHeaderBand, {
            props: { header: makeHeader() },
        });
        expect(wrapper.find('.project-name').text()).toBe('Riverside Dig');
    });

    it('joins the meta line with a middot', () => {
        const wrapper = mount(PermitHeaderBand, {
            props: { header: makeHeader() },
        });
        expect(wrapper.find('.permit-meta').text()).toContain(
            'APP-42 · Permit Application - Standard · Mining',
        );
    });

    it('drops empty parts from the meta line without stray middots', () => {
        const wrapper = mount(PermitHeaderBand, {
            props: { header: makeHeader({ submissionType: '' }) },
        });
        const text = wrapper.find('.permit-meta').text();
        // The empty submission type is dropped: one join middot, not two.
        expect(text).toContain('APP-42 · Mining');
        expect(text).not.toContain('· ·');
        expect(wrapper.find('.meta-unset').exists()).toBe(false);
    });

    it('shows the unset-sector note when no sector is given', () => {
        const wrapper = mount(PermitHeaderBand, {
            props: { header: makeHeader({ sector: '' }) },
        });
        expect(wrapper.find('.meta-unset').exists()).toBe(true);
    });

    it('renders the actions slot when not yet submitted', () => {
        const wrapper = mount(PermitHeaderBand, {
            props: { header: makeHeader({ submittedDate: null }) },
            slots: { actions: '<button class="slotted">Submit</button>' },
        });
        expect(wrapper.find('.submitted-text').exists()).toBe(false);
        expect(wrapper.find('.slotted').exists()).toBe(true);
    });
});
