import { buildModuleSummary } from '@/bcap/apps/Permit/moduleSummary.ts';

describe('buildModuleSummary', () => {
    it('strips script from a hostile module name', () => {
        const html = buildModuleSummary({
            current_module: '<img src=x onerror=alert(1)>Bad',
            completed: 1,
            total: 2,
        });
        expect(html).not.toContain('onerror');
        expect(html).toContain('1/2 modules complete');
    });

    it('omits the current line once everything is complete', () => {
        expect(
            buildModuleSummary({ current_module: '', completed: 2, total: 2 }),
        ).toBe('2/2 modules complete');
    });

    it('is empty with no modules', () => {
        expect(
            buildModuleSummary({ current_module: '', completed: 0, total: 0 }),
        ).toBe('');
        expect(buildModuleSummary(undefined)).toBe('');
    });
});
