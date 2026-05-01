<script setup lang="ts">
import { ref, computed } from 'vue';
import type { PropType } from 'vue';
import Menu from 'primevue/menu';

const props = defineProps({
    activeTab: {
        type: String,
        default: 'my_projects',
    },
    lastUpdated: {
        type: Date,
        default: () => new Date(),
    },
    sortOptions: {
        type: Array as PropType<Array<{ label: string; value: string }>>,
        default: () => [],
    },
    currentSort: {
        type: String,
        default: 'default',
    },
    sortOrder: {
        type: String as PropType<'asc' | 'desc'>,
        default: 'asc',
    },
});

const emit = defineEmits([
    'update:activeTab',
    'update:search',
    'update:currentSort',
    'update:sortOrder',
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

// Sort Menu Logic
const sortMenu = ref();

const toggleSortMenu = (event: Event) => {
    sortMenu.value.toggle(event);
};

// Generates the PrimeVue menu items from the passed props
const sortMenuModel = computed(() => {
    return props.sortOptions.map((opt) => {
        const isActive = props.currentSort === opt.value;

        return {
            label: opt.label,
            icon: isActive
                ? props.sortOrder === 'asc' // Use props.sortOrder
                    ? 'fa-solid fa-caret-up'
                    : 'fa-solid fa-caret-down'
                : 'fa-solid fa-caret-up',

            class: `custom-hover-item ${isActive ? 'active-sort-item' : ''}`,

            command: () => {
                if (isActive) {
                    emit(
                        'update:sortOrder',
                        props.sortOrder === 'asc' ? 'desc' : 'asc',
                    );
                } else {
                    emit('update:currentSort', opt.value);

                    const wantsDescDefault = [
                        'default',
                        'capDate',
                        'footerDate',
                    ].includes(opt.value);

                    emit('update:sortOrder', wantsDescDefault ? 'desc' : 'asc');
                }
                emit('refresh');
            },
        };
    });
});

// Displays what is currently being sorted
const activeSortLabel = computed(() => {
    const found = props.sortOptions.find((o) => o.value === props.currentSort);
    return found ? found.label : 'Default';
});
</script>

<template>
    <div class="sorting-bar-container">
        <Menu
            ref="sortMenu"
            :model="sortMenuModel"
            :popup="true"
            class="custom-sort-menu"
        />

        <div class="segmented-control">
            <button
                class="segment-btn"
                :class="{ active: props.activeTab === 'my_projects' }"
                @click="selectTab('my_projects')"
            >
                My projects
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
                :class="{ active: props.activeTab === 'all' }"
                @click="selectTab('all')"
            >
                All
            </button>
        </div>

        <div class="search-section">
            <div class="search-bar-wrapper">
                <button
                    class="icon-btn"
                    @click="toggleSortMenu"
                    aria-label="Sort Options"
                    style="display: flex; gap: 5px"
                >
                    <i class="fa-solid fa-bars"></i>
                    <i
                        :class="[
                            'fa-solid',
                            props.sortOrder === 'asc'
                                ? 'fa-caret-up'
                                : 'fa-caret-down',
                        ]"
                        style="font-size: 0.8rem; margin-top: 2px"
                    ></i>
                </button>

                <input
                    type="text"
                    v-model="searchQuery"
                    @input="handleSearchInput"
                    class="search-input"
                    placeholder="Search projects..."
                />

                <button
                    class="icon-btn search-submit-btn"
                    aria-label="Search"
                >
                    <i class="fa-solid fa-magnifying-glass"></i>
                </button>
            </div>

            <div
                v-if="props.currentSort !== 'default'"
                class="sort-indicator"
            >
                <span>
                    Sorted by:
                    <strong>{{ activeSortLabel }}</strong>
                </span>
                <i
                    :class="[
                        'fa-solid',
                        props.sortOrder === 'asc'
                            ? 'fa-arrow-up-wide-short'
                            : 'fa-arrow-down-wide-short',
                    ]"
                ></i>

                <i
                    class="fa-solid fa-circle-xmark clear-sort"
                    @click="emit('update:currentSort', 'default')"
                    title="Clear sort"
                ></i>
            </div>
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
    gap: 2.25rem;
    padding: 1.5rem 0;
    width: 100%;
    font-family: 'BC Sans', 'Noto Sans', sans-serif;
}

.flex-spacer {
    flex-grow: 1;
}

.segmented-control {
    display: flex;
    background-color: #ffffff;
    border-radius: 6px;
    overflow: hidden;
    box-shadow: 0 1.5px 4px rgba(0, 0, 0, 0.05);
}

.segment-btn {
    background: transparent;
    border: none;
    padding: 0.9rem 1.875rem;
    font-size: 1.425rem;
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
.search-section {
    position: relative;
    display: flex;
    flex-direction: column;
}

.search-bar-wrapper {
    display: flex;
    align-items: center;
    background-color: #ffffff;
    border-radius: 75px;
    padding: 0.45rem 1.5rem;
    width: 350px;
    box-shadow: 0 1.5px 4px rgba(0, 0, 0, 0.05);
}

.search-input {
    flex-grow: 1;
    border: none;
    background: transparent;
    padding: 0.6rem 0.75rem;
    font-size: 1.425rem;
    color: #333;
    outline: none;
}

.icon-btn {
    background: transparent;
    border: none;
    color: #555555;
    cursor: pointer;
    font-size: 1.5rem;
    padding: 0.3rem;
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
    gap: 0.75rem;
    padding: 0.6rem 1.5rem;
    border-radius: 75px;
    border: 1.5px solid #d1d5db;
    color: #555555;
    font-size: 1.35rem;
    cursor: pointer;
    transition: background-color 0.2s ease;
}

.status-pill:hover {
    background-color: #f3f4f6;
}

.refresh-icon {
    font-size: 1.275rem;
}

/* 4. Sort Additions */
.sort-indicator {
    position: absolute;
    top: 100%;
    left: 1.5rem;
    margin-top: 0.5rem;
    font-size: 1.15rem;
    color: #555555;
    display: flex;
    align-items: center;
    gap: 0.6rem;
}

.clear-sort {
    cursor: pointer;
    color: #999999;
    font-size: 1.2rem;
    transition: color 0.2s ease;
}

.clear-sort:hover {
    color: #d90000;
}
</style>

<style>
/* Custom Sort Menu Styles, I hate primevue */
.custom-sort-menu {
    --surface-hover: #003366 !important;
    --p-menu-item-focus-background: #003366 !important;
    --p-menu-item-focus-color: #ffffff !important;
}

.custom-hover-item:hover,
.custom-hover-item:hover > .p-menuitem-content,
.custom-hover-item:hover > .p-menuitem-link {
    background-color: #003366 !important;
    color: #ffffff !important;
}

.custom-hover-item:hover .p-menuitem-text,
.custom-hover-item:hover .p-menuitem-icon {
    color: #ffffff !important;
}

.custom-sort-menu,
.custom-sort-menu * {
    outline: none !important;
    box-shadow: none !important;
    border-color: transparent !important;

    --p-focus-ring: none !important;
    --p-focus-ring-width: 0px !important;
    --p-focus-ring-color: transparent !important;
    --p-focus-ring-offset: 0px !important;
}

.custom-sort-menu .p-menuitem:not(.active-sort-item) .p-menuitem-icon {
    opacity: 0.3;
}

.active-sort-item .p-menuitem-icon {
    opacity: 1 !important;
    color: #ffffff !important;
    transform: scale(1.2);
}
</style>
