<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import GenericWidget from '@/arches_vue_components/generics/GenericWidget/GenericWidget.vue';
import { EDIT } from '@/arches_vue_components/widgets/constants.ts';
import FieldSet from 'primevue/fieldset';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Message from 'primevue/message';
import Button from 'primevue/button';
import InputText from 'primevue/inputtext';
import type { CardXNodeXWidgetData } from '@/arches_vue_components/types.ts';
import type { AliasedNodeData } from '@/arches_vue_components/types.ts';
import { useDraftStep } from '@/bcap/composables/useDraftStep.ts';
import {
    fetchPmbcParcel,
    fetchWfsIntersect,
    type CrownTenureFeature,
} from '@/bcap/apps/Permit/api.ts';
import { area as turfArea } from '@turf/turf';

const CROWN_TENURES_LAYER = 'WHSE_TANTALIS.TA_CROWN_TENURES_SVW';

const { draftData, isValid, updateValue } = useDraftStep();

const mapOverrides = {
    widget: {
        widgetid: '',
        component:
            'bcgov_arches_common/widgets/MapDropZoneWidget/MapDropZoneWidget.vue',
    },
} satisfies Partial<CardXNodeXWidgetData>;

const boundaryHectares = computed(() => {
    const geom =
        draftData.value?.project_location?.aliased_data
            ?.service_request_boundary?.node_value;
    if (!geom) return null;
    try {
        return turfArea(geom as Parameters<typeof turfArea>[0]) / 10000;
    } catch {
        return null;
    }
});

// ----- PID parcel lookup -----

interface PidEntry {
    pid: string;
    loading: boolean;
    error: string;
    featureIds: string[];
}

const pidInput = ref('');
const pidLookupError = ref('');
const pidEntries = ref<PidEntry[]>([]);

function normalizePid(raw: string): string {
    return raw.replace(/\D/g, '');
}

function currentBoundary() {
    return draftData.value?.project_location?.aliased_data
        ?.service_request_boundary;
}

function currentFeatures(): unknown[] {
    return (
        (currentBoundary()?.node_value as { features?: unknown[] } | null)
            ?.features ?? []
    );
}

function setBoundaryFeatures(features: unknown[]) {
    const existing = currentBoundary();
    const newGeom = features.length
        ? { type: 'FeatureCollection', features }
        : null;
    updateValue(
        {
            ...(existing ?? { display_value: '', details: [] }),
            node_value: newGeom,
        } as AliasedNodeData,
        'service_request_boundary',
        'project_location',
    );
}

async function lookupPid() {
    const pid = normalizePid(pidInput.value);
    if (pid.length < 7) {
        pidLookupError.value = 'Enter a valid PID (e.g. 000-000-000).';
        return;
    }
    if (pidEntries.value.some((e) => e.pid === pid)) {
        pidLookupError.value = `PID ${pid} is already added.`;
        return;
    }
    pidLookupError.value = '';
    pidInput.value = '';

    const entry: PidEntry = { pid, loading: true, error: '', featureIds: [] };
    pidEntries.value.push(entry);

    try {
        const features = await fetchPmbcParcel(pid);
        if (!features.length) {
            entry.error = `No parcel found for PID ${pid}.`;
            return;
        }
        entry.featureIds = features.map((f) => String(f.id ?? ''));
        setBoundaryFeatures([...currentFeatures(), ...features]);
    } catch {
        entry.error = `Could not fetch parcel for PID ${pid}.`;
    } finally {
        entry.loading = false;
    }
}

function removePid(pid: string) {
    const idx = pidEntries.value.findIndex((e) => e.pid === pid);
    if (idx === -1) return;
    const idsToRemove = new Set(pidEntries.value[idx].featureIds);
    pidEntries.value.splice(idx, 1);
    if (!idsToRemove.size) return;
    const remaining = (currentFeatures() as { id?: string }[]).filter(
        (f) => !idsToRemove.has(f.id ?? ''),
    );
    setBoundaryFeatures(remaining);
}

// ----- Crown Tenure intersect -----

const tenures = ref<CrownTenureFeature[]>([]);
const tenuresLoading = ref(false);
const tenuresError = ref('');

watch(
    () =>
        draftData.value?.project_location?.aliased_data
            ?.service_request_boundary,
    async (boundary) => {
        const geom = boundary?.node_value as
            { type?: string; features?: unknown[] } | null | undefined;
        const hasFeatures =
            geom &&
            (geom.type !== 'FeatureCollection' ||
                (geom.features?.length ?? 0) > 0);
        if (!hasFeatures) {
            tenures.value = [];
            return;
        }
        tenuresLoading.value = true;
        tenuresError.value = '';
        try {
            tenures.value = await fetchWfsIntersect(
                CROWN_TENURES_LAYER,
                geom as object,
                'SHAPE',
            );
        } catch (error) {
            console.error(error);
            tenuresError.value =
                'Could not load Crown Tenure information. Please try again.';
        } finally {
            tenuresLoading.value = false;
        }
    },
);

defineExpose({ isValid });
</script>

<template>
    <FieldSet legend="">
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="
                draftData?.project_location?.aliased_data
                    ?.service_request_boundary
            "
            :card-x-node-x-widget-data-overrides="mapOverrides"
            graph-slug="bcap_service_request"
            node-alias="service_request_boundary"
            @update:aliased-node-data="
                updateValue(
                    $event,
                    'service_request_boundary',
                    'project_location',
                )
            "
        />
        <p
            v-if="boundaryHectares !== null"
            class="boundary-area"
        >
            Total area: {{ boundaryHectares.toFixed(2) }} ha
        </p>

        <div class="pid-lookup">
            <p class="pid-lookup-label">Add parcels by PID</p>
            <div class="pid-input-row">
                <InputText
                    v-model="pidInput"
                    placeholder="000-000-000"
                    @keyup.enter="lookupPid"
                />
                <Button
                    label="Add"
                    :disabled="!pidInput.trim()"
                    @click="lookupPid"
                />
            </div>
            <small
                v-if="pidLookupError"
                class="pid-error"
            >
                {{ pidLookupError }}
            </small>
            <div
                v-for="entry in pidEntries"
                :key="entry.pid"
                class="pid-chip"
            >
                <span class="pid-chip-label">{{ entry.pid }}</span>
                <span
                    v-if="entry.loading"
                    class="pid-chip-status"
                >
                    Loading…
                </span>
                <span
                    v-else-if="entry.error"
                    class="pid-chip-status pid-chip-status--error"
                >
                    {{ entry.error }}
                </span>
                <Button
                    icon="pi pi-times"
                    text
                    rounded
                    size="small"
                    :disabled="entry.loading"
                    aria-label="Remove PID"
                    @click="removePid(entry.pid)"
                />
            </div>
        </div>
    </FieldSet>

    <FieldSet
        v-if="tenuresLoading || tenuresError || tenures.length"
        legend="Intersecting Crown Tenures"
        class="tenures-panel"
    >
        <Message
            v-if="tenuresError"
            severity="error"
            :closable="false"
        >
            {{ tenuresError }}
        </Message>

        <p
            v-else-if="tenuresLoading"
            class="tenures-loading"
        >
            Loading Crown Tenure data…
        </p>

        <template v-else>
            <p class="tenures-count">
                {{ tenures.length }}
                Crown Tenure{{ tenures.length === 1 ? '' : 's' }} found within
                the service request boundary.
            </p>
            <DataTable
                :value="tenures"
                size="small"
                scrollable
                scroll-height="20rem"
            >
                <Column
                    field="properties.CROWN_LANDS_FILE"
                    header="File"
                />
                <Column
                    field="properties.TENURE_TYPE"
                    header="Type"
                />
                <Column
                    field="properties.TENURE_SUBTYPE"
                    header="Subtype"
                />
                <Column
                    field="properties.TENURE_PURPOSE"
                    header="Purpose"
                />
                <Column
                    field="properties.TENURE_STATUS"
                    header="Status"
                />
                <Column
                    field="properties.TENURE_HOLDER_NAME"
                    header="Holder"
                />
            </DataTable>
        </template>
    </FieldSet>
    <br />
</template>

<style scoped>
.tenures-panel {
    margin-top: 1rem;
}

.tenures-loading {
    color: var(--p-text-muted-color);
    font-style: italic;
}

.tenures-count {
    margin-bottom: 0.5rem;
}

.boundary-area {
    color: var(--p-text-muted-color);
    font-size: 1.2rem;
    margin-top: 0.5rem;
}

.pid-lookup {
    margin-top: 1rem;
}

.pid-lookup-label {
    font-weight: 600;
    margin-bottom: 0.5rem;
}

.pid-input-row {
    display: flex;
    gap: 0.5rem;
    align-items: center;
}

.pid-error {
    color: var(--p-red-500);
    display: block;
    margin-top: 0.25rem;
}

.pid-chip {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0.5rem;
    padding: 0.25rem 0.5rem;
    background: var(--p-surface-100);
    border-radius: var(--p-border-radius);
    width: fit-content;
}

.pid-chip-label {
    font-family: monospace;
}

.pid-chip-status {
    font-size: 0.8rem;
    color: var(--p-text-muted-color);
    font-style: italic;
}

.pid-chip-status--error {
    color: var(--p-red-500);
}
</style>
