<script setup lang="ts">
import { computed } from "vue";
import { getDisplayValue } from "@/bcap/util.ts";
import type { AliasedNodeData } from "@/arches_component_lab/types.ts";

interface Props {
    data: any[];
    contentPath: string;
    emptyMessage?: string;
    showItemNumbers?: boolean;
    itemClass?: string;
    wrapperClass?: string;
}

const props = withDefaults(defineProps<Props>(), {
    emptyMessage: "No items available.",
    showItemNumbers: false,
    itemClass: "html-content-item",
    wrapperClass: "html-content-list",
});

const getContentFromPath = (item: any, path: string): AliasedNodeData | null => {
    const pathParts = path.split('.');
    let current = item;

    for (const part of pathParts) {
        if (!current || typeof current !== 'object') return null;
        current = current[part];
    }

    return current as AliasedNodeData | null;
};

const processedItems = computed(() => {
    return props.data.map((item, index) => ({
        index,
        content: getDisplayValue(getContentFromPath(item, props.contentPath)),
        originalItem: item
    })).filter(item => item.content);
});
</script>

<template>
    <div :class="props.wrapperClass">
        <div v-if="processedItems.length > 0">
            <div
                v-for="item in processedItems"
                :key="item.index"
                :class="props.itemClass"
            >
                <h6 v-if="props.showItemNumbers" class="item-number">
                    Item {{ item.index + 1 }}
                </h6>
                <div
                    v-html="item.content"
                    class="html-content"
                ></div>
            </div>
        </div>
        <div v-else class="empty-state">
            <p>{{ props.emptyMessage }}</p>
        </div>
    </div>
</template>

<style scoped>
.html-content-list {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.html-content-item {
    padding: 1rem;
    background-color: #f8f9fa;
    border-radius: 4px;
    border-left: 4px solid #007bff;
}

.item-number {
    margin: 0 0 0.5rem 0;
    font-weight: 600;
    font-size: 0.9rem;
    color: #6c757d;
}

.html-content :deep(p) {
    margin-bottom: 0.5rem;
}

.html-content :deep(p:last-child) {
    margin-bottom: 0;
}

.html-content :deep(strong) {
    font-weight: 600;
    color: #495057;
}

.empty-state {
    padding: 1rem;
    text-align: center;
    color: #6c757d;
    font-style: italic;
}
</style>
