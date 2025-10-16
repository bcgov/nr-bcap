import DOMPurify from 'dompurify';
import type { AliasedNodeData } from '@/arches_component_lab/types.ts';

export const sanitizeHtml = (html: string | undefined): string => {
    if (!html) return '';
    return DOMPurify.sanitize(html);
};

export const formatDateTime = (isoString: string | null): string | null => {
    if (!isoString) return null;

    const date = new Date(isoString);
    const dateStr = date.toLocaleDateString('en-CA');

    const timeStr = date
        .toLocaleTimeString('en-US', {
            hour: 'numeric',
            minute: '2-digit',
            second: '2-digit',
            hour12: true,
        })
        .toLowerCase()
        .replace('am', 'a.m.')
        .replace('pm', 'p.m.');

    return `${dateStr}, ${timeStr}`;
};

/** Resolve a key (inside aliased_data) to an AliasedNodeData */
function getNode(row: unknown, key: string): AliasedNodeData | null {
    if (!row || typeof row !== 'object') return null;

    const aliased = (row as Record<string, unknown>)?.['aliased_data'];
    if (!aliased || typeof aliased !== 'object') return null;

    const cur = (aliased as Record<string, unknown>)?.[key];
    if (!cur || typeof cur !== 'object') return null;

    const maybe = cur as Partial<AliasedNodeData>;
    return 'display_value' in maybe && 'node_value' in maybe
        ? (maybe as AliasedNodeData)
        : null;
}

export const getDisplayValue = (value: AliasedNodeData | null | undefined) => {
    return value?.node_value ? value.display_value : '';
};

export const getNodeDisplayValue = (row: unknown, path: string) => {
    return getDisplayValue(getNode(row, path));
};

export const isEmpty = (value: AliasedNodeData | null | undefined): boolean => {
    return !value?.node_value;
};

export function isAliasedNodeData(value: unknown): value is AliasedNodeData {
    if (!value || typeof value !== 'object') return false;
    const maybe = value as Partial<AliasedNodeData>;
    return (
        'display_value' in maybe && 'node_value' in maybe && 'details' in maybe
    );
}
