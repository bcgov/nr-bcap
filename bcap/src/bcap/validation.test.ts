import { describe, it, expect } from 'vitest';
import * as z from 'zod';
import { isFilled, buildTileValidation } from './validation';
import type { AliasedNodeData } from '@/arches_component_lab/types.ts';

const node = (overrides: Partial<AliasedNodeData> = {}): AliasedNodeData => ({
    display_value: '',
    node_value: undefined,
    details: [],
    ...overrides,
});

describe('isFilled', () => {
    it('is false for an empty node_value', () => {
        expect(isFilled(null)).toBe(false);
        expect(isFilled(undefined)).toBe(false);
        expect(isFilled(node({ node_value: null }))).toBe(false);
        expect(isFilled(node({ node_value: '' }))).toBe(false);
    });

    it('string node_values (date, concept uuid, non-localized)', () => {
        expect(isFilled(node({ node_value: '2026-06-26' }))).toBe(true);
        expect(isFilled(node({ node_value: '   ' }))).toBe(false);
    });

    it('localized string node_values', () => {
        expect(isFilled(node({ node_value: { en: { value: 'hi' } } }))).toBe(
            true,
        );
        expect(isFilled(node({ node_value: { en: { value: '' } } }))).toBe(
            false,
        );
        expect(isFilled(node({ node_value: { en: { value: null } } }))).toBe(
            false,
        );
    });

    it('array node_values (reference, file-list, resource-instance-list)', () => {
        expect(isFilled(node({ node_value: [] }))).toBe(false);
        expect(isFilled(node({ node_value: [{ uri: 'x' }] }))).toBe(true);
    });

    it('geojson node_values', () => {
        expect(isFilled(node({ node_value: { features: [] } }))).toBe(false);
        expect(isFilled(node({ node_value: { features: [{}] } }))).toBe(true);
    });

    it('resource-instance node_values', () => {
        expect(isFilled(node({ node_value: { resourceId: '' } }))).toBe(false);
        expect(isFilled(node({ node_value: { resourceId: 'abc' } }))).toBe(
            true,
        );
    });

    it('url node_values', () => {
        expect(isFilled(node({ node_value: { url: '' } }))).toBe(false);
        expect(isFilled(node({ node_value: { url: 'https://x' } }))).toBe(true);
    });

    it('boolean / number node_values are filled when present', () => {
        expect(isFilled(node({ node_value: true }))).toBe(true);
        expect(isFilled(node({ node_value: false }))).toBe(true);
        expect(isFilled(node({ node_value: 0 }))).toBe(true);
    });
});

describe('buildTileValidation', () => {
    const leaf = z.object({
        display_value: z.string().optional(),
        node_value: z.unknown(),
    });
    const schema = z.object({
        required_field: leaf.nullable(), // non-optional => required
        optional_field: leaf.nullish(), // optional => not required
    });

    it('derives required aliases from non-optional schema fields', () => {
        const { requiredAliases } = buildTileValidation(schema);
        expect(requiredAliases).toEqual(['required_field']);
    });

    it('isComplete is false until every required field is filled', () => {
        const { isComplete } = buildTileValidation(schema);
        expect(isComplete(undefined)).toBe(false);
        expect(isComplete({})).toBe(false);
        expect(isComplete({ required_field: node({ node_value: 'x' }) })).toBe(
            true,
        );
    });

    it('ignores optional fields for completeness', () => {
        const { isComplete } = buildTileValidation(schema);
        expect(
            isComplete({
                required_field: node({ node_value: 'x' }),
                optional_field: null,
            }),
        ).toBe(true);
    });

    it('exposes a resolver function', () => {
        const { resolver } = buildTileValidation(schema);
        expect(typeof resolver).toBe('function');
    });
});
