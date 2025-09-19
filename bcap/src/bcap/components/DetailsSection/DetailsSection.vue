<script setup lang="ts">
import { computed, ref, watch } from "vue";
import FieldSet from "primevue/fieldset";
import ProgressSpinner from "primevue/progressspinner";

const props = defineProps<{
    sectionTitle: string;
    visible?: boolean;
    loading?: boolean;
    variant?: "section" | "subsection";
    forceCollapsed?: boolean;
}>();

const sectionVisible = ref(props.visible ?? true);
const isLoading = computed(() => props.loading ?? false);
const componentVariant = computed(() => props.variant ?? "section");

watch(
    () => props.forceCollapsed,
    (newValue: boolean | undefined) => {
        if (newValue !== undefined) {
            sectionVisible.value = !newValue;
        }
    },
    { immediate: false },
);
</script>

<template>
    <FieldSet
        v-if="componentVariant === 'section'"
        :collapsed="!sectionVisible"
        :legend="props.sectionTitle"
        :toggleable="true"
    >
        <ProgressSpinner
            v-if="isLoading"
            :style="{ width: '2rem', height: '2rem' }"
        />
        <slot
            v-else
            name="sectionContent"
        ></slot>
    </FieldSet>

    <div
        v-else
        class="subsection-wrapper"
    >
        <div
            class="subsection-header"
            @click="sectionVisible = !sectionVisible"
        >
            <i
                class="subsection-toggle-icon"
                :class="
                    sectionVisible
                        ? 'pi pi-chevron-down'
                        : 'pi pi-chevron-right'
                "
            ></i>
            <h4 class="subsection-title">{{ props.sectionTitle }}</h4>
        </div>

        <div
            v-if="sectionVisible"
            class="subsection-content"
        >
            <ProgressSpinner
                v-if="isLoading"
                :style="{ width: '2rem', height: '2rem' }"
            />
            <slot
                v-else
                name="sectionContent"
            ></slot>
        </div>
    </div>
</template>

<style>
legend.p-fieldset-legend {
    width: unset;
    margin-bottom: 0;
    font-size: 1.75rem;
}

.subsection-wrapper {
    margin: 2rem 0;
    padding-left: 1rem;
}

.subsection-header {
    display: flex;
    align-items: center;
    cursor: pointer;
    padding: 0.5rem 0;
    user-select: none;
}

.subsection-header:hover {
    background-color: #f8f9fa;
    margin: 0 -0.5rem;
    padding: 0.5rem;
    border-radius: 4px;
}

.subsection-toggle-icon {
    margin-right: 0.5rem;
    font-size: 0.875rem;
    color: #6c757d;
    transition: transform 0.2s ease;
}

.subsection-title {
    font-size: 1.5rem;
    font-weight: 800;
    margin: 0;
}

.subsection-content {
    margin-top: 0.75rem;
    padding-left: 1.25rem;
}
</style>
