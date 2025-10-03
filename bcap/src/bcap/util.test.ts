import { describe, it, expect } from 'vitest';
import {
    formatDateTime,
    getDisplayValue,
    getNodeDisplayValue,
    isEmpty,
    isAliasedNodeData,
} from './util';

// Helper to build rows like the app does
function rowWithAliased(key: string, value: unknown) {
    return { aliased_data: { [key]: value } } as const;
}

describe('formatDateTime', () => {
    it('returns null for null input', () => {
        expect(formatDateTime(null)).toBeNull();
    });

    it('formats a typical PM time with seconds and Canadian date', () => {
        // Local-time ISO without timezone to avoid environment tz flakiness
        const iso = '2025-06-21T13:05:09'; // 1:05:09 PM local time
        expect(formatDateTime(iso)).toBe('2025-06-21, 1:05:09 p.m.');
    });

    it('formats a typical AM time and uses a.m. suffix', () => {
        const iso = '2025-06-21T00:05:09'; // 12:05:09 AM local time
        expect(formatDateTime(iso)).toBe('2025-06-21, 12:05:09 a.m.');
    });

    it('handles invalid date strings without throwing (returns "Invalid Date")', () => {
        const out = formatDateTime('not a date' as unknown as string);
        // Implementation doesn't validate the Date, so it formats the Invalid Date object.
        expect(typeof out).toBe('string');
        // Both en-CA and en-US locales yield "Invalid Date" for invalid Date objects.
        expect(out).toMatch(/^Invalid Date, /);
        expect(out!.toLowerCase()).toContain('invalid date');
    });
});

describe('getDisplayValue', () => {
    it('returns empty string for null/undefined', () => {
        expect(getDisplayValue(null as any)).toBe('');
        expect(getDisplayValue(undefined as any)).toBe('');
    });

    it('returns empty string when node_value is falsy ("", 0, false, null)', () => {
        expect(
            getDisplayValue({
                display_value: 'X',
                node_value: '',
                details: [],
            } as any),
        ).toBe('');
        expect(
            getDisplayValue({
                display_value: 'X',
                node_value: 0,
                details: [],
            } as any),
        ).toBe('');
        expect(
            getDisplayValue({
                display_value: 'X',
                node_value: false,
                details: [],
            } as any),
        ).toBe('');
        expect(
            getDisplayValue({
                display_value: 'X',
                node_value: null,
                details: [],
            } as any),
        ).toBe('');
    });

    it('returns display_value when node_value is truthy', () => {
        expect(
            getDisplayValue({
                display_value: 'Shown',
                node_value: 123,
                details: [],
            } as any),
        ).toBe('Shown');
        expect(
            getDisplayValue({
                display_value: 'Shown',
                node_value: 'value',
                details: [],
            } as any),
        ).toBe('Shown');
        expect(
            getDisplayValue({
                display_value: 'Shown',
                node_value: { a: 1 },
                details: [],
            } as any),
        ).toBe('Shown');
    });
});

describe('getNodeDisplayValue (integration with getNode)', () => {
    it('returns empty string if row is null or not an object', () => {
        expect(getNodeDisplayValue(null as any, 'k')).toBe('');
        expect(getNodeDisplayValue(42 as any, 'k')).toBe('');
    });

    it('returns empty when aliased_data is missing or not an object', () => {
        expect(getNodeDisplayValue({} as any, 'k')).toBe('');
        expect(getNodeDisplayValue({ aliased_data: 'nope' } as any, 'k')).toBe(
            '',
        );
    });

    it('returns empty when key is missing or not an object', () => {
        expect(getNodeDisplayValue(rowWithAliased('k', undefined), 'k')).toBe(
            '',
        );
        expect(
            getNodeDisplayValue(rowWithAliased('k', 'not-an-object'), 'k'),
        ).toBe('');
    });

    it('returns empty when object is missing required AliasedNodeData props', () => {
        expect(
            getNodeDisplayValue(
                rowWithAliased('k', { node_value: 'v', details: [] }),
                'k',
            ),
        ).toBe(''); // missing display_value

        expect(
            getNodeDisplayValue(
                rowWithAliased('k', { display_value: 'X', details: [] }),
                'k',
            ),
        ).toBe(''); // missing node_value
    });

    it('returns display_value when a valid AliasedNodeData object has truthy node_value', () => {
        const row = rowWithAliased('path.to.thing', {
            display_value: 'Pretty',
            node_value: 'raw',
            details: [],
        });
        expect(getNodeDisplayValue(row, 'path.to.thing')).toBe('Pretty');
    });

    it('returns empty when a valid AliasedNodeData object has falsy node_value', () => {
        const row = rowWithAliased('x', {
            display_value: 'Hidden',
            node_value: '',
            details: [],
        });
        expect(getNodeDisplayValue(row, 'x')).toBe('');
    });
});

describe('isEmpty', () => {
    it('treats null/undefined as empty', () => {
        expect(isEmpty(null as any)).toBe(true);
        expect(isEmpty(undefined as any)).toBe(true);
    });

    it('treats falsy node_value as empty', () => {
        expect(
            isEmpty({ display_value: 'X', node_value: 0, details: [] } as any),
        ).toBe(true);
        expect(
            isEmpty({ display_value: 'X', node_value: '', details: [] } as any),
        ).toBe(true);
        expect(
            isEmpty({
                display_value: 'X',
                node_value: false,
                details: [],
            } as any),
        ).toBe(true);
        expect(
            isEmpty({
                display_value: 'X',
                node_value: null,
                details: [],
            } as any),
        ).toBe(true);
    });

    it('treats truthy node_value as not empty', () => {
        expect(
            isEmpty({ display_value: 'X', node_value: 1, details: [] } as any),
        ).toBe(false);
        expect(
            isEmpty({
                display_value: 'X',
                node_value: 'y',
                details: [],
            } as any),
        ).toBe(false);
    });
});

describe('isAliasedNodeData (type guard)', () => {
    it('returns false for non-objects or null', () => {
        expect(isAliasedNodeData(null as any)).toBe(false);
        expect(isAliasedNodeData(123 as any)).toBe(false);
        expect(isAliasedNodeData('x' as any)).toBe(false);
    });

    it('returns false when required keys are missing', () => {
        expect(
            isAliasedNodeData({ display_value: 'X', node_value: 'v' } as any),
        ).toBe(false);
        expect(isAliasedNodeData({ node_value: 'v', details: [] } as any)).toBe(
            false,
        );
        expect(
            isAliasedNodeData({ display_value: 'X', details: [] } as any),
        ).toBe(false);
    });

    it('returns true when display_value, node_value, and details keys exist (regardless of value types)', () => {
        expect(
            isAliasedNodeData({
                display_value: 'X',
                node_value: 'v',
                details: [],
            }),
        ).toBe(true);

        // Even if node_value is falsy, the shape still matches
        expect(
            isAliasedNodeData({
                display_value: 'X',
                node_value: '',
                details: [],
            }),
        ).toBe(true);
    });
});
