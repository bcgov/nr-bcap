<script setup lang="ts">
import { computed } from 'vue';
import Button from 'primevue/button';
import GenericWidget from '@/arches_component_lab/generics/GenericWidget/GenericWidget.vue';
import { EDIT, VIEW } from '@/arches_component_lab/widgets/constants.ts';
import type { AliasedNodeData } from '@/arches_component_lab/types.ts';

const props = withDefaults(
    defineProps<{
        maxItems?: number;
        addingNew: boolean;
        disableAddOrSave: boolean;
        graphSlug: string;
        nodeAlias: string;
        currentNodeData: unknown;
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        items: any[];
        selectedIndex: number;
        itemTypeLabel?: string;
        iconClass?: string;
    }>(),
    {
        maxItems: 10,
        itemTypeLabel: 'Document',
        iconClass: 'fa-file',
    },
);

const itemsCount = computed(() => props.items?.length || 0);
const hasUnsavedFile = computed(
    () => props.currentNodeData !== null && props.currentNodeData !== undefined,
);

const emit = defineEmits<{
    (e: 'file-updated', value: AliasedNodeData): void;
    (e: 'clear-pending'): void;
    (e: 'add-new'): void;
    (e: 'save-item'): void;
    (e: 'delete-item', index: number): void;
    (e: 'select-item', index: number): void;
}>();

const getFileName = (fileData: unknown): string => {
    const defaultName = props.itemTypeLabel || 'File';
    if (!fileData || typeof fileData !== 'object') return defaultName;
    const typedData = fileData as Record<string, unknown>;

    if (
        typedData.node_value &&
        Array.isArray(typedData.node_value) &&
        typedData.node_value.length > 0
    ) {
        const firstFile = typedData.node_value[0] as Record<string, unknown>;
        const fileName =
            (firstFile.name as string) || (firstFile.file as File)?.name || '';
        if (fileName) return fileName;
    }

    if (typeof typedData.display_value === 'string') {
        try {
            const parsed = JSON.parse(typedData.display_value) as Array<
                Record<string, unknown>
            >;
            if (
                Array.isArray(parsed) &&
                parsed.length > 0 &&
                typeof parsed[0].name === 'string'
            ) {
                return parsed[0].name;
            }
        } catch {
            return typedData.display_value || defaultName;
        }
    }

    return defaultName;
};

const isImage = (fileData: unknown): boolean => {
    if (!fileData || typeof fileData !== 'object') return false;
    const typedData = fileData as Record<string, unknown>;

    let firstFile: Record<string, unknown> | undefined;

    if (
        Array.isArray(typedData.node_value) &&
        typedData.node_value.length > 0
    ) {
        firstFile = typedData.node_value[0] as Record<string, unknown>;
    } else if (typeof typedData.display_value === 'string') {
        try {
            const parsed = JSON.parse(typedData.display_value);
            if (Array.isArray(parsed) && parsed.length > 0) {
                firstFile = parsed[0] as Record<string, unknown>;
            }
        } catch {
            /* parse errors */
        }
    }

    if (!firstFile) return false;

    const fileType =
        (firstFile.type as string) || (firstFile.file as File)?.type || '';
    const fileName =
        (firstFile.name as string) || (firstFile.file as File)?.name || '';

    return (
        fileType.startsWith('image/') ||
        /\.(jpeg|jpg|gif|png|webp|bmp|svg)$/i.test(fileName)
    );
};
</script>

<template>
    <div class="flex flex-row flex-nowrap uploader-layout">
        <div class="uploader-container">
            <div
                v-if="itemsCount >= maxItems && !hasUnsavedFile && addingNew"
                class="max-limit-message"
            >
                <i class="fa fa-ban limit-icon"></i>
                <div>
                    Maximum of {{ maxItems }} {{ itemTypeLabel.toLowerCase() }}s
                    reached.
                </div>
                <div class="limit-subtext">
                    Please delete a {{ itemTypeLabel.toLowerCase() }} to add
                    more.
                </div>
            </div>

            <GenericWidget
                v-else-if="!hasUnsavedFile && addingNew"
                :key="selectedIndex"
                :graph-slug="graphSlug"
                :node-alias="nodeAlias"
                :should-show-label="false"
                :mode="EDIT"
                :aliased-node-data="currentNodeData"
                @update:value="emit('file-updated', $event)"
            />

            <div
                v-else
                class="pending-doc-preview"
            >
                <GenericWidget
                    v-if="isImage(currentNodeData)"
                    :key="`view-${selectedIndex}`"
                    :graph-slug="graphSlug"
                    :node-alias="nodeAlias"
                    :should-show-label="false"
                    :mode="VIEW"
                    :aliased-node-data="currentNodeData"
                />
                <div
                    v-else
                    class="document-icon-wrapper"
                >
                    <i
                        class="fa-regular document-icon"
                        :class="iconClass"
                    ></i>
                    <span
                        class="document-name"
                        :title="getFileName(currentNodeData)"
                    >
                        {{ getFileName(currentNodeData) }}
                    </span>
                </div>
                <Button
                    v-if="addingNew"
                    :label="`Remove / Change ${itemTypeLabel}`"
                    icon="fa fa-times"
                    @click="emit('clear-pending')"
                />
            </div>
        </div>

        <div class="placeholders">
            <div>
                <Button
                    v-if="!addingNew && itemsCount < maxItems"
                    label="+ Add"
                    class="inline-block"
                    @click="emit('add-new')"
                />
                <Button
                    v-if="addingNew && itemsCount < maxItems"
                    class="inline-block"
                    :aria-disabled="disableAddOrSave"
                    :disabled="disableAddOrSave"
                    :tooltip="`Save the new ${itemTypeLabel.toLowerCase()} before adding another`"
                    @click="emit('save-item')"
                >
                    <i class="fa fa-save mr-2"></i>
                    Save {{ itemTypeLabel }}
                </Button>
            </div>

            <div class="flex flex-row doc-placeholders">
                <div
                    v-for="(item, index) in items"
                    :key="index"
                    :data-selected="index === selectedIndex"
                    class="doc-placeholder"
                    @click="emit('select-item', index)"
                >
                    <div
                        class="fa fa-remove doc-delete-icon"
                        :tooltip="`Remove ${itemTypeLabel}`"
                        @click.stop="emit('delete-item', index)"
                    ></div>
                    <div class="document-icon-wrapper-small">
                        <GenericWidget
                            v-if="isImage(item.aliased_data[nodeAlias])"
                            :graph-slug="graphSlug"
                            :mode="VIEW"
                            :should-show-label="false"
                            :node-alias="nodeAlias"
                            :aliased-node-data="item.aliased_data[nodeAlias]"
                        />
                        <template v-else>
                            <i
                                class="fa-regular document-icon-small"
                                :class="iconClass"
                            ></i>
                            <span
                                class="document-name-small"
                                :title="
                                    getFileName(item.aliased_data[nodeAlias])
                                "
                            >
                                {{ getFileName(item.aliased_data[nodeAlias]) }}
                            </span>
                        </template>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.uploader-layout {
    display: flex;
    gap: 1.5rem;
    flex-direction: row;
    align-items: start;
    flex-wrap: nowrap;
}

.uploader-container {
    width: 300px;
    min-height: 200px;
}

.max-limit-message {
    width: 100%;
    height: 100%;
    min-height: 200px;
    background: #f8f9fa;
    border: 2px dashed #dee2e6;
    border-radius: 6px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: #495057;
    font-weight: 600;
}

.limit-icon {
    font-size: 2rem;
    margin-bottom: 0.5rem;
    color: #aaa;
}

.limit-subtext {
    font-size: 0.8em;
    color: #666;
}

.pending-doc-preview {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

/* image previews */
.pending-doc-preview :deep(img) {
    max-width: 100%;
    max-height: 250px;
    object-fit: contain;
    border-radius: 4px;
}

.document-icon-wrapper {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 2rem 1rem;
    background: #f8f9fa;
    border: 1px solid #ddd;
    border-radius: 4px;
    text-align: center;
}

.document-icon {
    font-size: 3.5rem;
    color: #6c757d;
    margin-bottom: 0.75rem;
}

.document-name {
    font-size: 0.9rem;
    color: #495057;
    font-weight: 500;
    word-break: break-all;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.doc-placeholders {
    flex-flow: wrap;
    gap: 0.5rem;
    margin-top: 0.5rem;
    display: flex;
    flex-direction: row;
}

.doc-placeholder {
    max-width: 125px;
    min-width: 125px;
    height: 125px;
    position: relative;
    overflow: hidden;
    cursor: pointer;
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 0.5rem;
    transition: all 0.2s ease;
}

.doc-placeholder:hover {
    border-color: #adb5bd;
    background: #e9ecef;
}

.document-icon-wrapper-small {
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 100%;
}

/* thumbnail images */
.document-icon-wrapper-small :deep(img) {
    max-width: 100%;
    max-height: 100px;
    object-fit: cover;
    border-radius: 4px;
}

.document-icon-small {
    font-size: 2.25rem;
    color: #6c757d;
    margin-bottom: 0.5rem;
}

.document-name-small {
    font-size: 0.75rem;
    color: #495057;
    text-align: center;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    width: 100%;
}

.doc-delete-icon {
    position: absolute;
    top: 0.25rem;
    right: 0.25rem;
    color: #dc3545;
    cursor: pointer;
    background: rgba(255, 255, 255, 0.9);
    border-radius: 50%;
    width: 1.5rem;
    height: 1.5rem;
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.doc-delete-icon:hover {
    background: #dc3545;
    color: white;
}

.doc-placeholder[data-selected='false'] {
    opacity: 0.6;
}
.doc-placeholder[data-selected='true'] {
    border-color: #007bff;
    box-shadow: 0 0 0 1px #007bff;
}
</style>
