import DOMPurify from 'dompurify';
import type { AliasedNodeData } from '@/arches_component_lab/types.ts';
import type { ArchesDraftData } from '@/bcap/types.ts';

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

export const currentDateValue = function () {
    const now = new Date().toISOString().split('T')[0];
    return {
        display_value: now,
        node_value: now,
        details: [] as never[],
    };
};

export const getCsrfToken = (): string => {
    return (
        document.cookie
            .split('; ')
            .find((row) => row.startsWith('csrftoken='))
            ?.split('=')[1] || ''
    );
};

export const saveFieldToBackend = async (
    draftId: string,
    graphSlug: string,
    fullDraftData: ArchesDraftData,
) => {
    try {
        const patchUrl = `/bcap/api/resource_draft/${graphSlug}/${draftId}`;

        const response = await fetch(patchUrl, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
            },
            body: JSON.stringify({
                data: fullDraftData,
            }),
        });

        if (!response.ok) {
            throw new Error(`Server returned ${response.status}`);
        }

        console.log('Successfully auto-saved full draft data.');
    } catch (error) {
        console.error('Failed to auto-save draft data:', error);
    }
};

let globalTimeoutId: ReturnType<typeof setTimeout>;

export const updateDraftValue = (
    draftDataValue: ArchesDraftData | undefined,
    draftId: string | null | undefined,
    graphSlug: string,
    newValue: AliasedNodeData,
    attribute_name: string,
    node_group_alias: string | string[],
) => {
    if (!draftDataValue) return;

    const groups = Array.isArray(node_group_alias)
        ? node_group_alias
        : [node_group_alias];

    let currentLevel = draftDataValue as Record<string, unknown>;

    groups.forEach((group, index) => {
        const match = group.match(/^(.+)\[(\d+)\]$/);

        if (match) {
            const name = match[1];
            const arrIndex = parseInt(match[2], 10);

            if (!currentLevel[name]) currentLevel[name] = [];
            const arr = currentLevel[name] as Record<string, unknown>[];

            if (!arr[arrIndex]) arr[arrIndex] = { aliased_data: {} };

            if (index === groups.length - 1) {
                const target = arr[arrIndex].aliased_data as Record<
                    string,
                    unknown
                >;
                target[attribute_name] = newValue;
            } else {
                currentLevel = arr[arrIndex].aliased_data as Record<
                    string,
                    unknown
                >;
            }
        } else {
            if (!currentLevel[group])
                currentLevel[group] = { aliased_data: {} };
            const node = currentLevel[group] as {
                aliased_data: Record<string, unknown>;
            };

            if (index === groups.length - 1) {
                node.aliased_data[attribute_name] = newValue;
            } else {
                currentLevel = node.aliased_data;
            }
        }
    });

    clearTimeout(globalTimeoutId);

    globalTimeoutId = setTimeout(() => {
        if (draftId) {
            saveFieldToBackend(draftId, graphSlug, draftDataValue);
        }
    }, 1000);
};
