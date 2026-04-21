<script setup lang="ts">
import { ref, computed } from 'vue';

const props = defineProps({
    activeTab: {
        type: String,
        default: 'my_projects',
    },
    lastUpdated: {
        type: Date,
        default: () => new Date(),
    },
});

const emit = defineEmits([
    'update:activeTab',
    'update:search',
    'menu-click',
    'refresh',
]);
const searchQuery = ref('');

const formattedTime = computed(() => {
    if (!props.lastUpdated) return '';
    return new Intl.DateTimeFormat('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
    })
        .format(props.lastUpdated)
        .replace(',', '');
});

const selectTab = (tabId: string) => {
    emit('update:activeTab', tabId);
};

const handleSearchInput = () => {
    emit('update:search', searchQuery.value);
};
</script>

<template>
    <div class="sorting-bar-container">
        <div class="segmented-control">
            <button
                class="segment-btn"
                :class="{ active: props.activeTab === 'all' }"
                @click="selectTab('all')"
            >
                All
            </button>
            <button
                class="segment-btn"
                :class="{ active: props.activeTab === 'unassigned' }"
                @click="selectTab('unassigned')"
            >
                Unassigned
            </button>
            <button
                class="segment-btn"
                :class="{ active: props.activeTab === 'my_projects' }"
                @click="selectTab('my_projects')"
            >
                My projects
            </button>
        </div>

        <div class="search-bar-wrapper">
            <button
                class="icon-btn"
                @click="$emit('menu-click')"
                aria-label="Menu"
            >
                <i class="fa-solid fa-bars"></i>
            </button>

            <input
                type="text"
                v-model="searchQuery"
                @input="handleSearchInput"
                class="search-input"
            />

            <button
                class="icon-btn search-submit-btn"
                aria-label="Search"
            >
                <i class="fa-solid fa-magnifying-glass"></i>
            </button>
        </div>

        <div class="flex-spacer"></div>

        <div
            class="status-pill"
            @click="$emit('refresh')"
            role="button"
        >
            <i class="fa-solid fa-rotate-right refresh-icon"></i>
            lastupdated - {{ formattedTime }}
        </div>
    </div>
</template>

<style scoped>
/* Main Container */
.sorting-bar-container {
    display: flex;
    align-items: center;
    gap: 2.25rem; /* Scaled from 1.5rem */
    padding: 1.5rem 0; /* Scaled from 1rem */
    width: 100%;
    font-family: 'BC Sans', 'Noto Sans', sans-serif;
}

.flex-spacer {
    flex-grow: 1;
}

/* 1. Segmented Control */
.segmented-control {
    display: flex;
    background-color: #ffffff;
    border-radius: 6px; /* Scaled from 4px */
    overflow: hidden;
    box-shadow: 0 1.5px 4px rgba(0, 0, 0, 0.05);
}

.segment-btn {
    background: transparent;
    border: none;
    padding: 0.9rem 1.875rem; /* Scaled from 0.6rem 1.25rem */
    font-size: 1.425rem; /* Scaled from 0.95rem */
    color: #333333;
    cursor: pointer;
    transition: background-color 0.2s ease;
    border-right: 1.5px solid #eeeeee;
}

.segment-btn:last-child {
    border-right: none;
}

.segment-btn:hover {
    background-color: #f9f9f9;
}

.segment-btn.active {
    background-color: #e2e2e2;
    font-weight: 500;
}

/* 2. Search Bar */
.search-bar-wrapper {
    display: flex;
    align-items: center;
    background-color: #ffffff;
    border-radius: 75px; /* Scaled from 50px */
    padding: 0.45rem 1.5rem; /* Scaled from 0.3rem 1rem */
    width: 350px; /* Scaled from 350px */
    box-shadow: 0 1.5px 4px rgba(0, 0, 0, 0.05);
}

.search-input {
    flex-grow: 1;
    border: none;
    background: transparent;
    padding: 0.6rem 0.75rem; /* Scaled from 0.4rem 0.5rem */
    font-size: 1.425rem; /* Scaled from 0.95rem */
    color: #333;
    outline: none;
}

.icon-btn {
    background: transparent;
    border: none;
    color: #555555;
    cursor: pointer;
    font-size: 1.5rem; /* Scaled from 1rem */
    padding: 0.3rem; /* Scaled from 0.2rem */
    display: flex;
    align-items: center;
    justify-content: center;
}

.icon-btn:hover {
    color: #003366;
}

/* 3. Status Pill */
.status-pill {
    display: flex;
    align-items: center;
    gap: 0.75rem; /* Scaled from 0.5rem */
    padding: 0.6rem 1.5rem; /* Scaled from 0.4rem 1rem */
    border-radius: 75px; /* Scaled from 50px */
    border: 1.5px solid #d1d5db; /* Scaled from 1px */
    color: #555555;
    font-size: 1.35rem; /* Scaled from 0.9rem */
    cursor: pointer;
    transition: background-color 0.2s ease;
}

.status-pill:hover {
    background-color: #f3f4f6;
}

.refresh-icon {
    font-size: 1.275rem; /* Scaled from 0.85rem */
}
</style>
