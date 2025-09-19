<script setup lang="ts">
import { ref, computed, watch } from "vue";
import Button from "primevue/button";

const emit = defineEmits<{
    "visibility-changed": [hideEmpty: boolean];
    "collapse-all": [];
    "expand-all": [];
}>();

const hideEmptySections = ref(false);
const allCollapsed = ref(false);

const hideEmptyText = computed(() =>
    hideEmptySections.value ? "Show Empty Sections" : "Hide Empty Sections",
);

const collapseExpandText = computed(() =>
    allCollapsed.value ? "Expand All" : "Collapse All",
);

watch(hideEmptySections, (newValue) => {
    emit("visibility-changed", newValue);
});

const toggleCollapseExpand = () => {
    allCollapsed.value = !allCollapsed.value;

    if (allCollapsed.value) {
        emit("collapse-all");
    } else {
        emit("expand-all");
    }
};
</script>

<template>
    <div class="section-controls">
        <div class="control-group">
            <Button
                :label="hideEmptyText"
                :icon="hideEmptySections ? 'pi pi-eye-slash' : 'pi pi-eye'"
                class="control-button"
                severity="secondary"
                @click="hideEmptySections = !hideEmptySections"
            />

            <Button
                :label="collapseExpandText"
                :icon="allCollapsed ? 'pi pi-plus' : 'pi pi-minus'"
                class="control-button"
                severity="primary"
                @click="toggleCollapseExpand"
            />
        </div>
    </div>
</template>

<style scoped>
.section-controls {
    display: flex;
    justify-content: flex-end;
    margin-top: 3rem;
    padding: 0;
}

.control-group {
    display: flex;
    gap: 1rem;
    align-items: center;
}

.control-button {
    min-width: 180px;
    font-size: 1.2rem;
    font-weight: 500;
}

@media (max-width: 768px) {
    .section-controls {
        justify-content: center;
    }

    .control-group {
        flex-direction: column;
        width: 100%;
        gap: 0.75rem;
    }

    .control-button {
        width: 100%;
        min-width: auto;
    }
}
</style>
