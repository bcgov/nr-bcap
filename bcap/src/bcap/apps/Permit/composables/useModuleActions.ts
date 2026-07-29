import { computed, reactive, watch } from 'vue';
import {
    patchModuleOrder,
    removeModuleAndRequirements,
    submitModule,
    reorderModuleRequirements,
    addBlankRequirement,
    removeRequirement,
    setModuleCompleted,
    setRequirementSatisfied,
} from '@/bcap/apps/Permit/api.ts';
import type { GraphSlug } from '@/bcap/apps/Permit/graphSlug.ts';
import { useConfirmAction } from '@/bcap/apps/Permit/composables/useConfirmAction.ts';
import {
    cacheSatisfied,
    hydrateRows,
    rowsNeedingDetails,
    toRow,
    type AddableModule,
    type ModuleRow,
    type RequirementItem,
} from '@/bcap/apps/Permit/components/filing-summary/modules/moduleRows.ts';
import type { PermitApplicationProcessModuleTile } from '@/bcap/client/types.gen.ts';

// The module panel's rows and every write that changes them. The caller supplies
// the permit it is editing, a getter for the tiles (so the rows rebuild when the
// parent reloads), and onChanged for the writes that need a parent reload.
export const useModuleActions = (options: {
    permitId: string;
    adminTileId: string;
    tiles: () => PermitApplicationProcessModuleTile[];
    onChanged: () => void;
}) => {
    const { permitId, adminTileId, tiles, onChanged } = options;

    const state = reactive({
        rows: [] as ModuleRow[],
        saving: false,
        loading: [] as string[],
    });

    const ui = reactive({
        openPanels: [] as string[],
        adding: null as string | null,
        addingRequirement: null as string | null,
        togglingModule: null as string | null,
        togglingRequirement: null as string | null,
    });

    const loadRequirementDetails = async (rows: ModuleRow[]) => {
        const rowsToLoad = rowsNeedingDetails(rows);
        if (!rowsToLoad.length) return;
        const tileids = rowsToLoad.map((row) => row.tileid);
        state.loading.push(...tileids);
        try {
            await hydrateRows(rowsToLoad);
        } finally {
            state.loading = state.loading.filter((id) => !tileids.includes(id));
        }
    };

    const isLoadingRequirements = (row: ModuleRow): boolean =>
        state.loading.includes(row.tileid);

    // Fetch statuses only for the modules whose panels are open, so opening a
    // permit doesn't chain a request for every module's requirements up front.
    const loadOpenModules = (openIds: string[]) => {
        const openRows = state.rows.filter((row) =>
            openIds.includes(row.tileid),
        );
        if (openRows.length) loadRequirementDetails(openRows);
    };

    let seededDefaultOpen = false;
    watch(
        tiles,
        (value) => {
            state.rows = (value || [])
                .filter((tile) => tile.tileid && tile.aliased_data?.module_name)
                .map(toRow)
                .sort((a, b) => a.order - b.order);
            // On first load, open the top module by default; afterward the
            // user's open/closed choices stand for the life of the view.
            if (!seededDefaultOpen) {
                seededDefaultOpen = true;
                if (!ui.openPanels.length && state.rows.length) {
                    ui.openPanels = [state.rows[0].tileid];
                }
            }
            loadOpenModules(ui.openPanels);
        },
        { immediate: true, deep: true },
    );

    watch(() => ui.openPanels, loadOpenModules, { deep: true });

    const hasModules = computed(() => state.rows.length > 0);

    const onAddModule = async (mod: AddableModule) => {
        if (ui.adding) return;
        ui.adding = mod.id;
        try {
            // Blank host: staff fill it in afterward via the module's edit links.
            await submitModule(permitId, undefined, mod.id as GraphSlug, {});
            onChanged();
        } catch (error) {
            console.error('Failed to add module:', error);
        } finally {
            ui.adding = null;
        }
    };

    const onToggleCompleted = async (row: ModuleRow) => {
        if (ui.togglingModule) return;
        ui.togglingModule = row.tileid;
        try {
            await setModuleCompleted(permitId, row.tileid, !row.isCompleted);
            onChanged();
        } catch (error) {
            console.error('Failed to change module completion:', error);
        } finally {
            ui.togglingModule = null;
        }
    };

    // Toggle a non-checklist requirement's satisfied status. Updates the row and
    // the detail cache in place so the status icon flips without a full reload.
    const onToggleRequirement = async (requirement: RequirementItem) => {
        if (ui.togglingRequirement) return;
        ui.togglingRequirement = requirement.resourceId;
        const next = !requirement.satisfied;
        try {
            await setRequirementSatisfied(requirement.resourceId, next);
            requirement.satisfied = next;
            cacheSatisfied(requirement.resourceId, next);
        } catch (error) {
            console.error('Failed to change requirement status:', error);
        } finally {
            ui.togglingRequirement = null;
        }
    };

    const onAddRequirement = async (row: ModuleRow) => {
        if (ui.addingRequirement) return;
        ui.addingRequirement = row.tileid;
        try {
            await addBlankRequirement(permitId, row.tileid);
            onChanged();
        } catch (error) {
            console.error('Failed to add requirement:', error);
        } finally {
            ui.addingRequirement = null;
        }
    };

    const moduleRemove = useConfirmAction<ModuleRow>(async (row) => {
        await removeModuleAndRequirements(permitId, row.tileid);
        onChanged();
    });

    const reqRemove = useConfirmAction<{
        row: ModuleRow;
        requirement: RequirementItem;
    }>(async ({ row, requirement }) => {
        await removeRequirement(permitId, row.tileid, requirement.resourceId);
        onChanged();
    });

    const persistReqOrder = (row: ModuleRow) =>
        reorderModuleRequirements(
            permitId,
            row.tileid,
            row.requirements.map((requirement) => requirement.resourceId),
        );

    const persistOrder = async () => {
        // Renumber from the new positions, then persist every tile's module_order.
        const ordered = state.rows.map((row, position) => ({
            ...row,
            order: position + 1,
        }));
        state.rows = ordered;
        state.saving = true;
        try {
            await patchModuleOrder(
                permitId,
                adminTileId,
                ordered.map((row) => ({
                    tileid: row.tileid,
                    order: row.order,
                    name: row.name,
                    moduleId: row.moduleId,
                })),
            );
        } catch (error) {
            console.error('Failed to save module order:', error);
        } finally {
            state.saving = false;
        }
    };

    return {
        state,
        ui,
        hasModules,
        isLoadingRequirements,
        onAddModule,
        onAddRequirement,
        onToggleCompleted,
        onToggleRequirement,
        moduleRemove,
        reqRemove,
        persistOrder,
        persistReqOrder,
    };
};
