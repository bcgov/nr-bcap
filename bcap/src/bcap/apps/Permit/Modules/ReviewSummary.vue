<script setup lang="ts">
import GenericWidget from '@/arches_component_lab/generics/GenericWidget/GenericWidget.vue';
import { VIEW } from '@/arches_component_lab/widgets/constants.ts';
import type { CardXNodeXWidgetData } from '@/arches_component_lab/types.ts';

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

const mapOverrides = {
    widget: {
        widgetid: '',
        component:
            'bcgov_arches_common/widgets/MapDropZoneWidget/MapDropZoneWidget.vue',
    },
} satisfies Partial<CardXNodeXWidgetData>;

const stripHtml = (html?: unknown) => {
    // Ensure we only try to parse strings
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

            <dd class="centered-map">
                <GenericWidget
                    :mode="VIEW"
                    :should-show-label="false"
                    :aliased-node-data="field.value"
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
    font-size: 1.35rem;
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
</style>
