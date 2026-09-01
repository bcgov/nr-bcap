<script setup lang="ts">
import GenericWidget from '@/arches_vue_components/generics/GenericWidget/GenericWidget.vue';
import { useMapFrameAutoCentre } from '@/bcgov_arches_common/composables/useMapFrameAutoCentre.ts';
import { VIEW } from '@/arches_vue_components/widgets/constants.ts';
import type {
    AliasedNodeData,
    CardXNodeXWidgetData,
} from '@/arches_vue_components/types.ts';

export interface ReviewField {
    label: string;
    value?: unknown;
    type?: 'text' | 'html' | 'map';
    nodeAlias?: string;
    graphSlug?: string;
}

defineProps<{
    fields: ReviewField[];
}>();

useMapFrameAutoCentre('mapBoxes');

const mapOverrides = {
    widget: {
        widgetid: '',
        component:
            'bcgov_arches_common/widgets/MapDropZoneWidget/MapDropZoneWidget.vue',
    },
} satisfies Partial<CardXNodeXWidgetData>;

const stripHtml = (html?: unknown) => {
    if (typeof html !== 'string' || !html) return '';
    const doc = new DOMParser().parseFromString(html, 'text/html');
    return doc.body.textContent || '';
};

const hasValue = (val: unknown): boolean => {
    if (val === null || val === undefined) return false;
    if (typeof val === 'string' && val.trim() === '') return false;
    if (typeof val === 'object') {
        if (Array.isArray(val) && val.length === 0) return false;
        if (
            !Array.isArray(val) &&
            Object.keys(val as Record<string, unknown>).length === 0
        ) {
            return false;
        }
    }

    return true;
};
</script>

<template>
    <div class="div-grid-cols">
        <template
            v-for="(field, index) in fields"
            :key="'text-' + index"
        >
            <template v-if="hasValue(field.value) && field.type !== 'map'">
                <dt>{{ field.label }}</dt>

                <dd v-if="field.type === 'html'">
                    {{ stripHtml(field.value) }}
                </dd>
                <dd v-else>
                    {{ field.value }}
                </dd>
            </template>
        </template>
    </div>

    <template
        v-for="(field, index) in fields"
        :key="'map-' + index"
    >
        <div
            v-if="hasValue(field.value) && field.type === 'map'"
            class="map-section"
        >
            <dt class="mb-2 font-bold">{{ field.label }}</dt>

            <dd
                ref="mapBoxes"
                class="centered-map"
            >
                <GenericWidget
                    :mode="VIEW"
                    :should-show-label="false"
                    :aliased-node-data="field.value as AliasedNodeData"
                    :card-x-node-x-widget-data-overrides="mapOverrides"
                    :graph-slug="field.graphSlug || 'permit_application'"
                    :node-alias="field.nodeAlias || 'project_boundary'"
                />
            </dd>
        </div>
    </template>
</template>

<style scoped>
.div-grid-cols {
    display: grid;
    grid-template-columns: 210px 1fr;
    gap: 1.3rem 1rem;
    align-items: start;
    font-size: 13px;
    line-height: 1.5;
}

.div-grid-cols dt {
    font-weight: 600;
    color: #000000;
}

.div-grid-cols dd {
    color: #000000;
    margin: 0;
}

.map-section {
    padding-top: 2rem;
    width: 100%;
    display: block;
}

/* Drag the corner to resize; the widget sizes off these vars, so they follow
   the box instead of its 750x500 defaults. */
.centered-map {
    resize: both;
    overflow: hidden;
    width: calc(100% - 4rem);
    max-width: calc(100% - 4rem);
    margin: 0 2rem;
    height: 20rem;
    min-height: 10rem;
    --map-width: 100%;
    --map-max-width: 100%;
    --map-max-height: 100%;
}

/* The widget's map div only carries a min-height, so it ignored the box being
   dragged; the observer above feeds it the box's pixels instead. */
.centered-map :deep(.map-wrap),
.centered-map :deep(.map) {
    height: 100%;
}

/* The map fills the box, so the readout rides over its bottom edge and the
   maplibre controls step up to clear it. */
.centered-map :deep(.map-wrap) {
    position: relative;
}

.centered-map :deep(.map-wrap > .panel) {
    position: absolute;
    inset: auto 0 0 0;
    z-index: 2;
    padding: 0.3rem 0.5rem 0.5rem;
    background-color: rgba(255, 255, 255, 0.85);
    font-size: 12px;
    line-height: 1.4;
}

.centered-map :deep(.maplibregl-ctrl-bottom-left),
.centered-map :deep(.maplibregl-ctrl-bottom-right) {
    bottom: 3.8rem;
}
</style>
