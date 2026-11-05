<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import GenericWidget from '@/arches_vue_components/generics/GenericWidget/GenericWidget.vue';
import { EDIT } from '@/arches_vue_components/widgets/constants.ts';
import FieldSet from 'primevue/fieldset';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Message from 'primevue/message';
import type { CardXNodeXWidgetData } from '@/arches_vue_components/types.ts';
import { useDraftStep } from '@/bcap/composables/useDraftStep.ts';
import {
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
        draftData.value?.proposed_project?.aliased_data?.project_boundary
            ?.node_value;
    if (!geom) return null;
    try {
        return turfArea(geom as Parameters<typeof turfArea>[0]) / 10000;
    } catch {
        return null;
    }
});

const tenures = ref<CrownTenureFeature[]>([]);
const tenuresLoading = ref(false);
const tenuresError = ref('');

watch(
    () => draftData.value?.proposed_project?.aliased_data?.project_boundary,
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
                draftData?.proposed_project?.aliased_data
                    ?.development_project_details?.aliased_data
                    ?.industrial_sector
            "
            graph-slug="permit_application"
            node-alias="industrial_sector"
            @update:aliased-node-data="
                updateValue($event, 'industrial_sector', [
                    'proposed_project',
                    'development_project_details',
                ])
            "
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="
                draftData?.proposed_project?.aliased_data?.project_boundary
            "
            :card-x-node-x-widget-data-overrides="mapOverrides"
            graph-slug="permit_application"
            node-alias="project_boundary"
            @update:aliased-node-data="
                updateValue($event, 'project_boundary', 'proposed_project')
            "
        />
        <p
            v-if="boundaryHectares !== null"
            class="boundary-area"
        >
            Total area: {{ boundaryHectares.toFixed(2) }} ha
        </p>
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
                the project boundary.
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
</style>
