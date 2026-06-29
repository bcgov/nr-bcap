import { ref } from 'vue';
import { defineStore } from 'pinia';
import { debounce } from 'underscore';
import { createDraft } from '@/bcap/apps/Permit/api.ts';
import { saveDraftFieldToBackend } from '@/bcap/api.ts';
import type { ArchesDraftData } from '@/bcap/types.ts';
import type { AliasedNodeData } from '@/arches_component_lab/types.ts';

const debouncedSave = debounce(
    async (
        draftData: ArchesDraftData,
        graphSlug: string,
        ensureDraftId: () => Promise<string>,
    ) => {
        const id = await ensureDraftId();
        if (id) saveDraftFieldToBackend(id, graphSlug, draftData);
    },
    1000,
);

// Write newValue into the nested aliased_data path, creating intermediate tiles
// and arrays as needed.
function setDraftValue(
    draftData: ArchesDraftData,
    newValue: AliasedNodeData,
    attribute_name: string,
    node_group_alias: string | string[],
) {
    const groups = Array.isArray(node_group_alias)
        ? node_group_alias
        : [node_group_alias];

    let currentLevel = draftData as Record<string, unknown>;

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
}

// The draft a workflow module is currently editing. The store is global and
// survives route changes, so each module resets it on mount via initDraft.
export const useDraftStore = defineStore('draft', () => {
    const draftId = ref<string | null>(null);
    const draftData = ref<ArchesDraftData>({});
    const graphSlug = ref('');
    const parentPermitId = ref<string | null>(null);

    let draftCreation: Promise<string> | null = null;

    function initDraft(slug: string, parent: string | null = null) {
        graphSlug.value = slug;
        parentPermitId.value = parent;
        draftId.value = null;
        draftData.value = {};
        draftCreation = null;
    }

    function loadDraft(id: string, data: ArchesDraftData) {
        draftId.value = id;
        draftData.value = data;
        draftCreation = null;
    }

    // Create the draft on first use, not on mount, so an abandoned form leaves
    // no empty draft behind. Memoized so rapid first saves don't duplicate.
    function ensureDraftId(): Promise<string> {
        if (draftId.value) return Promise.resolve(draftId.value);
        // Assign the in-flight promise synchronously so concurrent first edits
        // dedupe to one createDraft call.
        if (!draftCreation) {
            draftCreation = (async () => {
                try {
                    const draft = await createDraft(
                        graphSlug.value,
                        parentPermitId.value ?? undefined,
                    );
                    draftId.value = draft.id;
                    return draft.id;
                } catch (error) {
                    // Clear the memo so the next edit retries instead of
                    // replaying this rejection forever.
                    draftCreation = null;
                    throw error;
                }
            })();
        }
        return draftCreation;
    }

    function updateValue(
        newValue: AliasedNodeData,
        attribute_name: string,
        node_group_alias: string | string[],
    ) {
        setDraftValue(
            draftData.value,
            newValue,
            attribute_name,
            node_group_alias,
        );
        debouncedSave(draftData.value, graphSlug.value, ensureDraftId);
    }

    return {
        draftId,
        draftData,
        graphSlug,
        parentPermitId,
        initDraft,
        loadDraft,
        ensureDraftId,
        updateValue,
    };
});
