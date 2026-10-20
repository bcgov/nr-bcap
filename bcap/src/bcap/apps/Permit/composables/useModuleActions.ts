import { computed, onScopeDispose, reactive, watch } from 'vue';
import { inlineMessage, notifyError } from '@/bcap/notify.ts';
import {
    patchModuleOrder,
    removeModuleAndRequirements,
    reorderModuleRequirements,
    addBlankRequirement,
    removeRequirement,
    setModuleCompleted,
    setRequirementSatisfied,
    setRequirementAssignee,
    fetchAssignableContributors,
} from '@/bcap/apps/Permit/api.ts';
import { useConfirmAction } from '@/bcap/apps/Permit/composables/useConfirmAction.ts';
import {
    cacheSatisfied,
    clearRequirementCache,
    hydrateRows,
    rowsNeedingDetails,
    toRow,
    type ModuleRow,
    type RequirementItem,
} from '@/bcap/apps/Permit/components/filing-summary/modules/moduleRows.ts';
import type {
    ContributorSummary,
    PermitApplicationProcessModuleTile,
} from '@/bcap/client/types.gen.ts';

// The module panel's rows and every write that changes them. The caller supplies
// the permit it is editing, a getter for the tiles (so the rows rebuild when the
// parent reloads), and onChanged for the writes that need a parent reload.
export const useModuleActions = (options: {
    permitId: string;
    adminTileId: string;
    tiles: () => PermitApplicationProcessModuleTile[];
    onChanged: () => void;
    // Requirement to open the view on, in place of the default first module.
    focusRequirementId?: string;
}) => {
    const { permitId, adminTileId, tiles, onChanged, focusRequirementId } =
        options;
    clearRequirementCache();
    onScopeDispose(clearRequirementCache);

    const state = reactive({
        rows: [] as ModuleRow[],
        saving: false,
        loading: [] as string[],
        loadError: '',
        assignees: [] as ContributorSummary[],
    });

    const ui = reactive({
        openPanels: [] as string[],
        addingRequirement: null as string | null,
        togglingModule: null as string | null,
        togglingRequirement: null as string | null,
    });

    const loadRequirementDetails = async (rows: ModuleRow[]) => {
        const rowsToLoad = rowsNeedingDetails(rows);
        if (!rowsToLoad.length) return;
        const tileids = rowsToLoad.map((row) => row.tileid);
        state.loading.push(...tileids);
        state.loadError = '';
        try {
            await hydrateRows(rowsToLoad);
        } catch (error) {
            state.loadError = inlineMessage(error);
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
                    const focused = focusRequirementId
                        ? state.rows.find((row) =>
                              row.requirements.some(
                                  (requirement) =>
                                      requirement.resourceId ===
                                      focusRequirementId,
                              ),
                          )
                        : undefined;
                    ui.openPanels = [(focused ?? state.rows[0]).tileid];
                }
            }
            loadOpenModules(ui.openPanels);
        },
        { immediate: true, deep: true },
    );

    watch(() => ui.openPanels, loadOpenModules, { deep: true });

    const hasModules = computed(() => state.rows.length > 0);

    const onToggleCompleted = async (row: ModuleRow) => {
        if (ui.togglingModule) return;
        ui.togglingModule = row.tileid;
        try {
            await setModuleCompleted(permitId, row.tileid, !row.isCompleted);
            onChanged();
        } catch (error) {
            notifyError('Failed to change module completion', error);
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
            notifyError('Failed to change requirement status', error);
        } finally {
            ui.togglingRequirement = null;
        }
    };

    const loadAssignees = async () => {
        if (state.assignees.length) {
            return;
        }
        try {
            state.assignees = await fetchAssignableContributors();
        } catch (error) {
            notifyError('Failed to load assignable contributors', error);
        }
    };

    const onAssignRequirement = async (
        row: ModuleRow,
        requirement: RequirementItem,
        contributorId: string | null,
    ) => {
        const previous = { ...requirement };
        const assignee = state.assignees.find(
            (one) => one.id === contributorId,
        );
        requirement.ministryAssigneeId = assignee?.id ?? '';
        requirement.ministryAssignee = assignee?.name ?? '';
        try {
            await setRequirementAssignee(
                permitId,
                row.tileid,
                requirement.resourceId,
                contributorId,
            );
        } catch (error) {
            notifyError('Failed to set requirement assignee', error);
            Object.assign(requirement, previous);
        }
    };

    const onAddRequirement = async (row: ModuleRow) => {
        if (ui.addingRequirement) return;
        ui.addingRequirement = row.tileid;
        try {
            await addBlankRequirement(permitId, row.tileid);
            onChanged();
        } catch (error) {
            notifyError('Failed to add requirement', error);
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
            notifyError('Failed to save module order', error);
        } finally {
            state.saving = false;
        }
    };

    return {
        state,
        ui,
        hasModules,
        isLoadingRequirements,
        onAddRequirement,
        onToggleCompleted,
        onToggleRequirement,
        onAssignRequirement,
        loadAssignees,
        moduleRemove,
        reqRemove,
        persistOrder,
        persistReqOrder,
    };
};
