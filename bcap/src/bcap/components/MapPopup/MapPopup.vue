<script setup lang="ts">
import { computed, isRef, onMounted, ref } from 'vue';
import type { Ref } from 'vue';
import _ from 'underscore';
import mapPopupProvider from 'utils/map-popup-provider';

import type {
    DescriptorsType,
    PopupFeatureType,
    DescriptorKey,
    Translations,
} from '@/bcap/components/MapPopup/types.ts';
import type { BcapURLs } from '@/bcap/types.ts';

const props = defineProps<{
    loading: boolean;
    urls: BcapURLs;
    popupFeatures: PopupFeatureType[];
    translations: Translations;
    showEditButton: boolean;
    showFilterByFeatureButton: boolean;
}>();

const emit = defineEmits(['advance-feature', 'send-feature-to-map-filter']);
const visibleFeature = ref();
const features = ref([] as Ref<PopupFeatureType>[]);
const activeFeatureOffset = ref(0);

function advanceFeature(direction: string) {
    if (direction === 'left') {
        activeFeatureOffset.value =
            activeFeatureOffset.value === 0
                ? features.value.length - 1
                : activeFeatureOffset.value - 1;
    } else {
        activeFeatureOffset.value =
            activeFeatureOffset.value === features.value.length - 1
                ? 0
                : activeFeatureOffset.value + 1;
    }
    visibleFeature.value = features.value[activeFeatureOffset.value].value;
    // emit("advance-feature", direction);
}

const currentFeature = computed<PopupFeatureType>(() => {
    return features.value[activeFeatureOffset.value].value;
});

function showExpandButton(feature: PopupFeatureType | undefined) {
    if (!feature) return false;
    return typeof feature.showExpandButton === 'function'
        ? feature.showExpandButton()
        : !!feature.showExpandButton;
}

function openReport(id: string) {
    window.open(props.urls.resource_report + id);
}

function openEdit(id: string) {
    window.open(props.urls.resource_editor + id);
}

function sendFeatureToMapFilter(
    feature: PopupFeatureType,
    useAsFilter: boolean,
) {
    mapPopupProvider.sendFeatureToMapFilter(feature, useAsFilter);
    emit('send-feature-to-map-filter', feature, useAsFilter);
}

function showFilterByFeature(feature: PopupFeatureType | undefined) {
    if (!feature) return false;
    return typeof feature?.showFilterByFeature === 'function'
        ? feature.showFilterByFeature(feature)
        : false;
}

const descriptionProperties = [
    'displayname',
    'graph_name',
    'map_popup',
    'geometries',
];
function setDisplayValues() {
    props.popupFeatures.forEach((raw_feature: PopupFeatureType, index) => {
        raw_feature.displayValues = isRef(raw_feature.displayValues)
            ? raw_feature.displayValues
            : ref(raw_feature.displayValues);
        const feature: Ref<PopupFeatureType> = ref(raw_feature);
        features.value.push(feature);
        if (feature.value.active()) {
            visibleFeature.value = feature.value;
            activeFeatureOffset.value = index;
            console.log(`Setting index to ${index}`);
        }
        fetch(
            props.urls.resource_descriptors + feature.value.resourceinstanceid,
        )
            .then((response) => response.json())
            .then((data) => {
                const displayValues: Partial<DescriptorsType> = {};
                const keys = descriptionProperties as DescriptorKey[];

                keys.forEach((prop) => {
                    const val = data[prop];
                    if (typeof val === 'string') {
                        displayValues[prop] = data[prop];
                    }
                });
                feature.value.displayValues =
                    displayValues as Ref<DescriptorsType>;
                console.log(feature.value.displayValues);
                feature.value.permissions = data["permissions"];
                feature.value.loading = false;
            })
            .catch((error) => {
                console.log(error);
            });
    });
}

/* eslint-disable */
function getActiveFeature() {
    return _.find(
        props.popupFeatures,
        (feature: PopupFeatureType) => feature.active,
    );
}
/* eslint-enable */

onMounted(() => {
    console.log('Component is mounted!');
    setDisplayValues();
});
</script>
<template>
    <div
        v-if="visibleFeature?.loading"
        class="hover-feature-body hover-feature-loading"
    >
        <i class="fa fa-spin fa-spinner"></i>
        <span>{{ translations.loading }}...</span>
    </div>

    <template v-else>
        <div :key="visibleFeature?.resourceinstanceid">
            <div class="hover-feature-title-bar">
                <div style="display: flex">
                    <div
                        v-if="popupFeatures.length > 1"
                        class="hover-feature-nav-left"
                        @click="advanceFeature('left')"
                    >
                        <i class="fa fa-angle-left"></i>
                    </div>
                    <div
                        v-if="popupFeatures.length > 1"
                        class="hover-feature-nav-right"
                        @click="advanceFeature('right')"
                    >
                        <i class="fa fa-angle-right"></i>
                    </div>
                    <div class="hover-feature-title">
                        {{ visibleFeature?.displayValues?.displayname }}
                    </div>
                </div>
            </div>

            <div class="hover-feature-body">
                <!-- eslint-disable vue/no-v-html -->
                <div
                    class="hover-feature"
                    :style="{
                        '-webkit-line-clamp': visibleFeature?.showAll
                            ? '12'
                            : '4',
                        'overflow-y': visibleFeature?.showAll
                            ? 'scroll'
                            : 'hidden',
                    }"
                    v-html="visibleFeature?.map_popup()"
                ></div>

                <div
                    v-if="showExpandButton(visibleFeature)"
                    class="hover-feature-expand"
                    @click="visibleFeature.showAll = !visibleFeature.showAll"
                >
                    ...
                </div>

                <div
                    v-if="visibleFeature?.resourceinstanceid"
                    class="hover-feature-metadata-block"
                >
                    <div class="hover-feature-metadata">
                        <span>{{ translations.resourceModel }}</span>
                        <span>
                            {{ visibleFeature?.displayValues?.graph_name }}
                        </span>
                    </div>
                    <div class="hover-feature-metadata">
                        <span>{{ translations.idString }}</span>
                        <span>{{ visibleFeature?.resourceinstanceid }}</span>
                    </div>
                </div>
            </div>

            <div class="hover-feature-footer">
                <div>
                    <a
                        v-if="visibleFeature?.resourceinstanceid"
                        href="javascript:void(0)"
                        @click="
                            currentFeature?.mapCard.showDetailsFromFilter(
                                currentFeature.resourceinstanceid,
                            )
                        "
                    >
                        <i class="fa fa-info-circle"></i>
                        <span>Details</span>
                    </a>

                    <a
                        v-if="
                            visibleFeature?.resourceinstanceid && showEditButton
                        "
                        href="javascript:void(0)"
                        @click="openReport(visibleFeature?.resourceinstanceid)"
                    >
                        <i class="ion-document-text"></i>
                        <span>{{ translations.report }}</span>
                    </a>

                    <a
                        v-if="
                            visibleFeature?.resourceinstanceid && showEditButton
                        "
                        href="javascript:void(0)"
                        @click="openEdit(visibleFeature?.resourceinstanceid)"
                    >
                        <i class="ion-ios-refresh-empty"></i>
                        <span>{{ translations.edit }}</span>
                    </a>

                    <a
                        v-if="
                            showFilterByFeatureButton &&
                            showFilterByFeature(visibleFeature)
                        "
                        href="#"
                        style="padding-right: 2px"
                        @click.prevent="
                            sendFeatureToMapFilter(visibleFeature, true)
                        "
                    >
                        <i class="fa fa-filter"></i>
                        <span>{{ translations.filterByFeature }}</span>
                    </a>
                </div>

                <div
                    v-if="popupFeatures.length > 1"
                    style="
                        display: flex;
                        flex-direction: row;
                        width: 60px;
                        justify-content: space-evenly;
                        font-weight: 500;
                    "
                >
                    <div class="hover-feature-instance-counter">
                        {{ 1 + activeFeatureOffset }}
                    </div>
                    <span>{{ translations.of }}</span>
                    <div style="padding-left: 3px">
                        {{ popupFeatures.length }}
                    </div>
                </div>
            </div>
        </div>
    </template>
</template>

<style scoped>
.hover-feature-body {
    /* Your styling here */
}
</style>
