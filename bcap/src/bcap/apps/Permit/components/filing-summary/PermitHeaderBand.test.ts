import { mount } from '@vue/test-utils';
import PermitHeaderBand, { type PermitHeader } from './PermitHeaderBand.vue';

const makeHeader = (overrides: Partial<PermitHeader> = {}): PermitHeader => ({
    projectName: 'Riverside Dig',
    applicationNumber: 'APP-42',
    submissionType: 'Permit Application - Standard',
    sector: 'Mining',
    organization: 'Acme Corp',
    submittedDate: '2026-07-23',
    ...overrides,
});

const meta = (wrapper: ReturnType<typeof mount>) =>
    wrapper.findAll('.meta-part').map((part) => part.text());

describe('PermitHeaderBand', () => {
    it('titles the band with the project name and its file number', () => {
        const wrapper = mount(PermitHeaderBand, {
            props: { header: makeHeader() },
        });
        expect(wrapper.find('.project-name').text()).toBe('Riverside Dig');
        expect(wrapper.find('.application-number').text()).toBe('APP-42');
    });

    it('lists the organization, submission type, and sector', () => {
        const wrapper = mount(PermitHeaderBand, {
            props: { header: makeHeader() },
        });
        expect(meta(wrapper)).toEqual([
            'Acme Corp',
            'Permit Application - Standard',
            'Mining',
        ]);
        expect(wrapper.find('.meta-flag').exists()).toBe(false);
    });

    it('drops an empty part rather than leaving a stray separator', () => {
        const wrapper = mount(PermitHeaderBand, {
            props: { header: makeHeader({ organization: '' }) },
        });
        expect(meta(wrapper)).toEqual([
            'Permit Application - Standard',
            'Mining',
        ]);
    });

    it('flags a missing sector', () => {
        const wrapper = mount(PermitHeaderBand, {
            props: { header: makeHeader({ sector: '' }) },
        });
        expect(meta(wrapper)).toEqual([
            'Acme Corp',
            'Permit Application - Standard',
        ]);
        expect(wrapper.find('.meta-flag').text()).toBe('Sector not specified');
    });

    it('renders the actions slot', () => {
        const wrapper = mount(PermitHeaderBand, {
            props: { header: makeHeader({ submittedDate: null }) },
            slots: { actions: '<button class="slotted">Submit</button>' },
        });
        expect(wrapper.find('.slotted').exists()).toBe(true);
    });
});
