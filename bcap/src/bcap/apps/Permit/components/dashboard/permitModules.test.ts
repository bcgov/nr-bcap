import { GraphSlug } from '@/bcap/apps/Permit/graphSlug.ts';
import { FilingType } from '@/bcap/apps/Permit/filingType.ts';
import { modulesForFilingType, graphForModule } from './permitModules.ts';

const idsFor = (filingType: string) =>
    modulesForFilingType(filingType).map((mod) => mod.id);

describe('modulesForFilingType', () => {
    it('gives every permit application type the full set', () => {
        const full = [
            GraphSlug.BcapServiceRequest,
            GraphSlug.NoticeOfProjectIntent,
            GraphSlug.Investigation,
            GraphSlug.Inspection,
            GraphSlug.Alteration,
            GraphSlug.DocumentSubmission,
        ];
        expect(idsFor(FilingType.PermitApplicationStandard)).toEqual(full);
        expect(idsFor(FilingType.PermitApplicationEmergency)).toEqual(full);
        expect(idsFor(FilingType.PermitApplicationMultiProject)).toEqual(full);
        expect(idsFor(FilingType.ZoneAddition)).toEqual(full);
    });

    it('narrows a single-module filing type to its own module', () => {
        expect(idsFor(FilingType.SiteVisit)).toEqual([
            GraphSlug.BcapServiceRequest,
            GraphSlug.SiteVisit,
        ]);
        expect(idsFor(FilingType.DocumentSubmission)).toEqual([
            GraphSlug.BcapServiceRequest,
            GraphSlug.DocumentSubmission,
        ]);
        expect(idsFor(FilingType.InformationRequest)).toEqual([
            GraphSlug.BcapServiceRequest,
            GraphSlug.InformationRequest,
        ]);
    });

    it('heads every menu with Filing Summary', () => {
        for (const filingType of Object.values(FilingType)) {
            expect(idsFor(filingType)[0]).toBe(GraphSlug.BcapServiceRequest);
        }
    });

    it('falls back to the full set for an unrecognised type', () => {
        // A new filing_type list item should widen the menu, not empty it.
        const full = idsFor(FilingType.ZoneAddition);
        expect(idsFor('Something New')).toEqual(full);
        expect(idsFor('')).toEqual(full);
    });
});

describe('graphForModule', () => {
    it('matches a module name to its host graph slug', () => {
        expect(graphForModule('Investigation')).toBe(GraphSlug.Investigation);
        expect(graphForModule('Inspection')).toBe(GraphSlug.Inspection);
    });

    it('matches case-insensitively and by label substring', () => {
        expect(graphForModule('an alteration of the site')).toBe(
            GraphSlug.Alteration,
        );
    });

    it('never resolves to the service request itself', () => {
        expect(graphForModule('Filing Summary')).toBeUndefined();
    });

    it('returns undefined when nothing matches', () => {
        expect(graphForModule('Totally Unknown')).toBeUndefined();
    });
});
