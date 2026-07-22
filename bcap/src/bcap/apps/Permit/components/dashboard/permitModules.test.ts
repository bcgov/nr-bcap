import { describe, it, expect } from 'vitest';
import { GraphSlug } from '@/bcap/apps/Permit/graphSlug.ts';
import { FilingType } from '@/bcap/apps/Permit/filingType.ts';
import { modulesForFilingType } from './permitModules.ts';

const idsFor = (filingType: string) =>
    modulesForFilingType(filingType).map((mod) => mod.id);

describe('modulesForFilingType', () => {
    it('gives every permit application type the full set', () => {
        const full = [
            GraphSlug.PermitApplication,
            GraphSlug.NoticeOfProjectIntent,
            GraphSlug.Investigation,
            GraphSlug.Inspection,
            GraphSlug.Alteration,
        ];
        expect(idsFor(FilingType.PermitApplicationStandard)).toEqual(full);
        expect(idsFor(FilingType.PermitApplicationEmergency)).toEqual(full);
        expect(idsFor(FilingType.PermitApplicationMultiProject)).toEqual(full);
        expect(idsFor(FilingType.ZoneAddition)).toEqual(full);
    });

    it('narrows a single-module filing type to its own module', () => {
        expect(idsFor(FilingType.SiteVisit)).toEqual([
            GraphSlug.PermitApplication,
            GraphSlug.SiteVisit,
        ]);
        expect(idsFor(FilingType.DocumentSubmission)).toEqual([
            GraphSlug.PermitApplication,
            GraphSlug.DocumentSubmission,
        ]);
        expect(idsFor(FilingType.InformationRequest)).toEqual([
            GraphSlug.PermitApplication,
            GraphSlug.InformationRequest,
        ]);
    });

    it('heads every menu with Project Summary', () => {
        for (const filingType of Object.values(FilingType)) {
            expect(idsFor(filingType)[0]).toBe(GraphSlug.PermitApplication);
        }
    });

    it('falls back to the full set for an unrecognised type', () => {
        // A new filing_type list item should widen the menu, not empty it.
        const full = idsFor(FilingType.ZoneAddition);
        expect(idsFor('Something New')).toEqual(full);
        expect(idsFor('')).toEqual(full);
    });
});
