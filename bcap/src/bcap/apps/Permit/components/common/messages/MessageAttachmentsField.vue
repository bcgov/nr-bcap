<script setup lang="ts">
import GenericWidget from '@/arches_vue_components/generics/GenericWidget/GenericWidget.vue';
import { formatFileSize } from '@/bcap/util.ts';
import { GraphSlug } from '@/bcap/apps/Permit/graphSlug.ts';

const props = defineProps<{
    files: File[];
    // Changing this remounts the widget, clearing what it has staged.
    resetKey: string;
}>();

const emit = defineEmits<{ (e: 'update:files', files: File[]): void }>();

// The file widget emits an entry per staged file; the raw File rides in .file.
const onFilesSelected = (value: Array<{ file?: File }>) => {
    emit(
        'update:files',
        (value ?? [])
            .map((entry) => entry.file)
            .filter((file): file is File => Boolean(file)),
    );
};

const removeFile = (index: number) => {
    const remaining = [...props.files];
    remaining.splice(index, 1);
    emit('update:files', remaining);
};
</script>

<template>
    <div class="field-block attachments-field">
        <label class="field-label">
            Attachments
            <span class="field-optional">(optional)</span>
        </label>
        <div class="attachments-widget">
            <GenericWidget
                :key="resetKey"
                :graph-slug="GraphSlug.BcapMessage"
                node-alias="attachments"
                mode="edit"
                @update:value="
                    onFilesSelected($event as Array<{ file?: File }>)
                "
            />
        </div>

        <ul
            v-if="files.length"
            class="staged-attachments"
        >
            <li
                v-for="(file, index) in files"
                :key="`${file.name}-${index}`"
            >
                <i class="fa-regular fa-paperclip"></i>
                <span class="staged-name">{{ file.name }}</span>
                <span class="staged-size">{{ formatFileSize(file.size) }}</span>
                <button
                    type="button"
                    class="staged-remove"
                    aria-label="Remove attachment"
                    @click="removeFile(index)"
                >
                    <i class="fa-solid fa-xmark"></i>
                </button>
            </li>
        </ul>
    </div>
</template>

<style>
.attachments-field {
    margin-top: 1.25rem;
}

.attachments-widget label {
    display: none !important;
}

.attachments-widget input[type='file'] {
    display: none;
}

.attachments-widget .file-list {
    display: none !important;
}

.attachments-widget .p-fileupload,
.attachments-widget .p-fileupload-content {
    padding: 0;
    border: none;
    background: transparent;
}

.staged-attachments {
    list-style: none;
    margin: 0.6rem 0 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    flex: 0 0 auto;
}

.staged-attachments li {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    flex-shrink: 0;
    padding: 0.5rem 0.9rem;
    background-color: #eef2f7;
    border: 1px solid #d6dee8;
    border-radius: 8px;
    font-size: 1.2rem;
    color: var(--bc-navy);
}

.staged-name {
    flex: 1 1 auto;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.staged-size {
    flex: 0 0 auto;
    font-size: 1.05rem;
    color: #6c757d;
}

.staged-remove {
    flex: 0 0 auto;
    border: none;
    background: none;
    cursor: pointer;
    padding: 0.2rem 0.4rem;
    font-size: 1.2rem;
    color: #6c757d;
}

.staged-remove:hover {
    color: #d32f2f;
}
</style>
