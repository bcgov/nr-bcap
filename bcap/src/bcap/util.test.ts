import { describe, it, expect } from 'vitest';
import {
    formatDateTime,
    getDisplayValue,
    isEmpty,
    isAliasedNodeData,
} from './util';

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
        expect(getDisplayValue(null as unknown)).toBe('');
        expect(getDisplayValue(undefined as unknown)).toBe('');
    });

    it('returns empty string when node_value is falsy ("", 0, false, null)', () => {
        expect(
            getDisplayValue({
                display_value: 'X',
                node_value: '',
                details: [],
            } as unknown),
        ).toBe('');
        expect(
            getDisplayValue({
                display_value: 'X',
                node_value: 0,
                details: [],
            } as unknown),
        ).toBe('');
        expect(
            getDisplayValue({
                display_value: 'X',
                node_value: false,
                details: [],
            } as unknown),
        ).toBe('');
        expect(
            getDisplayValue({
                display_value: 'X',
                node_value: null,
                details: [],
            } as unknown),
        ).toBe('');
    });

    it('returns display_value when node_value is truthy', () => {
        expect(
            getDisplayValue({
                display_value: 'Shown',
                node_value: 123,
                details: [],
            } as unknown),
        ).toBe('Shown');
        expect(
            getDisplayValue({
                display_value: 'Shown',
                node_value: 'value',
                details: [],
            } as unknown),
        ).toBe('Shown');
        expect(
            getDisplayValue({
                display_value: 'Shown',
                node_value: { a: 1 },
                details: [],
            } as unknown),
        ).toBe('Shown');
    });
});

describe('isEmpty', () => {
    it('treats null/undefined as empty', () => {
        expect(isEmpty(null as unknown)).toBe(true);
        expect(isEmpty(undefined as unknown)).toBe(true);
    });

    it('treats falsy node_value as empty', () => {
        expect(
            isEmpty({
                display_value: 'X',
                node_value: 0,
                details: [],
            } as unknown),
        ).toBe(true);
        expect(
            isEmpty({
                display_value: 'X',
                node_value: '',
                details: [],
            } as unknown),
        ).toBe(true);
        expect(
            isEmpty({
                display_value: 'X',
                node_value: false,
                details: [],
            } as unknown),
        ).toBe(true);
        expect(
            isEmpty({
                display_value: 'X',
                node_value: null,
                details: [],
            } as unknown),
        ).toBe(true);
    });

    it('treats truthy node_value as not empty', () => {
        expect(
            isEmpty({
                display_value: 'X',
                node_value: 1,
                details: [],
            } as unknown),
        ).toBe(false);
        expect(
            isEmpty({
                display_value: 'X',
                node_value: 'y',
                details: [],
            } as unknown),
        ).toBe(false);
    });
});

describe('isAliasedNodeData (type guard)', () => {
    it('returns false for non-objects or null', () => {
        expect(isAliasedNodeData(null as unknown)).toBe(false);
        expect(isAliasedNodeData(123 as unknown)).toBe(false);
        expect(isAliasedNodeData('x' as unknown)).toBe(false);
    });

    it('returns false when required keys are missing', () => {
        expect(
            isAliasedNodeData({
                display_value: 'X',
                node_value: 'v',
            } as unknown),
        ).toBe(false);
        expect(
            isAliasedNodeData({ node_value: 'v', details: [] } as unknown),
        ).toBe(false);
        expect(
            isAliasedNodeData({ display_value: 'X', details: [] } as unknown),
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
