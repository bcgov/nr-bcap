<script setup lang="ts">
import { ref, computed } from 'vue';
import type { PropType } from 'vue';
import Button from 'primevue/button';
import Menu from 'primevue/menu';

const props = defineProps({
    activeTab: {
        type: String,
        default: 'my_projects',
    },
    tabs: {
        type: Array as PropType<Array<{ label: string; value: string }>>,
        default: () => [
            { label: 'My projects', value: 'my_projects' },
            { label: 'Unassigned', value: 'unassigned' },
            { label: 'All', value: 'all' },
        ],
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
    // Opt-in checkbox beside the tabs; omit the label to leave it out.
    messagesOnly: {
        type: Boolean,
        default: false,
    },
    messagesOnlyLabel: {
        type: String,
        default: '',
    },
    // Card counts for the results summary; omitted (or zero total) hides it.
    shown: {
        type: Number,
        default: 0,
    },
    total: {
        type: Number,
        default: 0,
    },
});

const emit = defineEmits([
    'update:activeTab',
    'update:search',
    'update:currentSort',
    'update:sortOrder',
    'update:messagesOnly',
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

const sortMenu = ref();

const toggleSortMenu = (event: Event) => {
    sortMenu.value.toggle(event);
};

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

// Each chip clears the one thing it names; the tab is a heading, not a chip,
// since there is no "no tab" state to clear it to.
const activeFilters = computed(() => {
    const filters = [];
    if (searchQuery.value)
        filters.push({
            key: 'search',
            label: `Search: ${searchQuery.value}`,
            clear: () => {
                searchQuery.value = '';
                handleSearchInput();
            },
        });
    if (props.messagesOnly && props.messagesOnlyLabel)
        filters.push({
            key: 'messages',
            label: props.messagesOnlyLabel,
            clear: () => emit('update:messagesOnly', false),
        });
    if (props.currentSort !== 'default')
        filters.push({
            key: 'sort',
            label: `Sort: ${activeSortLabel.value}`,
            clear: () => emit('update:currentSort', 'default'),
        });
    return filters;
});

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
            <Button
                v-for="tab in props.tabs"
                :key="tab.value"
                unstyled
                class="segment-btn"
                :class="{ active: props.activeTab === tab.value }"
                @click="selectTab(tab.value)"
            >
                {{ tab.label }}
            </Button>
        </div>

        <label
            v-if="props.messagesOnlyLabel"
            class="messages-filter"
        >
            <input
                type="checkbox"
                :checked="props.messagesOnly"
                @change="
                    emit(
                        'update:messagesOnly',
                        ($event.target as HTMLInputElement).checked,
                    )
                "
            />
            {{ props.messagesOnlyLabel }}
        </label>

        <div class="search-bar-wrapper">
            <i class="fa-solid fa-magnifying-glass search-icon"></i>
            <input
                v-model="searchQuery"
                type="text"
                class="search-input"
                placeholder="Search projects"
                @input="handleSearchInput"
            />
            <Button
                v-if="searchQuery"
                unstyled
                class="icon-btn"
                aria-label="Clear search"
                @click="
                    searchQuery = '';
                    handleSearchInput();
                "
            >
                <i class="fa-solid fa-xmark"></i>
            </Button>
        </div>

        <Button
            unstyled
            class="bar-btn sort-btn"
            aria-label="Sort Options"
            @click="toggleSortMenu"
        >
            <i class="fa-solid fa-filter"></i>
            Sort: {{ activeSortLabel }}
            <i
                v-if="props.currentSort !== 'default'"
                :class="[
                    'fa-solid',
                    props.sortOrder === 'asc' ? 'fa-caret-up' : 'fa-caret-down',
                ]"
            ></i>
        </Button>

        <div class="flex-spacer"></div>

        <span class="updated-text">Updated {{ formattedTime }}</span>

        <Button
            unstyled
            class="bar-btn refresh-btn"
            @click="$emit('refresh')"
        >
            <i class="fa-solid fa-rotate-right"></i>
            Refresh
        </Button>
    </div>

    <!-- Always rendered, so chips appearing don't push the cards down. -->
    <div class="filter-row">
        <div
            v-if="props.total"
            class="results-summary"
        >
            Showing
            <strong>{{ props.shown }}</strong>
            of
            <strong>{{ props.total }}</strong>
            cards
        </div>

        <div
            v-if="activeFilters.length"
            class="filter-chips"
        >
            <span class="filter-chips-label">Filters:</span>
            <button
                v-for="filter in activeFilters"
                :key="filter.key"
                type="button"
                class="filter-chip"
                @click="filter.clear()"
            >
                {{ filter.label }}
                <i class="fa-solid fa-xmark"></i>
            </button>
        </div>
    </div>
</template>

<style scoped>
.sorting-bar-container {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 1rem 2rem;
    padding: 1rem 0 1.25rem;
    width: 100%;
    box-sizing: border-box;
    font-family: 'BCSans', 'Noto Sans', sans-serif;
}

.flex-spacer {
    flex-grow: 1;
}

.segmented-control {
    display: flex;
    background-color: #ffffff;
    border: 1.5px solid #d1d5db;
    border-radius: 4px;
    overflow: hidden;
}

/* Sits beside the tabs, reading as a plain option rather than a fourth tab. */
.messages-filter {
    display: inline-flex;
    align-items: center;
    flex-shrink: 0;
    /* Pushes the search section to the far end so it can't ride over the label. */
    margin-right: auto;
    gap: 0.75rem;
    line-height: 1;
    font-size: 1.425rem;
    color: #333333;
    white-space: nowrap;
    cursor: pointer;
}

.messages-filter input {
    width: 1.6rem;
    height: 1.6rem;
    margin: 0;
    accent-color: var(--bc-navy);
    cursor: pointer;
}

.segment-btn {
    background: transparent;
    border: none;
    padding: 0.85rem 1.75rem;
    font-size: 1.425rem;
    color: #333333;
    cursor: pointer;
    transition:
        background-color 0.2s ease,
        color 0.2s ease;
    border-right: 1.5px solid #d1d5db;
}

.segment-btn:last-child {
    border-right: none;
}

.segment-btn:hover {
    background-color: #f3f4f6;
}

.segment-btn.active {
    background-color: var(--bc-navy, #003366);
    color: #ffffff;
    font-weight: 600;
}

.search-bar-wrapper {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    background-color: #ffffff;
    border: 1.5px solid #d1d5db;
    border-radius: 4px;
    padding: 0.35rem 1rem;
    flex: 1 1 220px;
    min-width: 0;
    max-width: 350px;
    box-sizing: border-box;
}

.search-bar-wrapper:focus-within {
    border-color: var(--bc-navy, #003366);
}

.search-icon {
    color: #6c757d;
    font-size: 1.35rem;
}

.search-input {
    flex-grow: 1;
    border: none;
    background: transparent;
    padding: 0.5rem 0;
    font-size: 1.425rem;
    color: #333;
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

.bar-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.75rem 1.25rem;
    border: 1.5px solid #d1d5db;
    border-radius: 4px;
    background-color: #ffffff;
    color: #333333;
    font-size: 1.425rem;
    white-space: nowrap;
    cursor: pointer;
    transition:
        background-color 0.2s ease,
        border-color 0.2s ease;
}

.bar-btn:hover {
    background-color: #f3f4f6;
    border-color: var(--bc-navy, #003366);
}

.refresh-btn {
    color: var(--bc-navy, #003366);
    font-weight: 600;
}

.updated-text {
    color: #6c757d;
    font-size: 1.3rem;
    white-space: nowrap;
}

.filter-row {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 1rem;
    height: 2.4rem;
    padding-bottom: 1rem;
    /* Owns the gap down to the first card, so both dashboards match. */
    margin-bottom: 1rem;
    border-bottom: 1.5px solid #e5e7eb;
    font-family: 'BCSans', 'Noto Sans', sans-serif;
}

.results-summary {
    margin-right: auto;
    color: #555555;
    font-size: 1.25rem;
}

.results-summary strong {
    color: var(--bc-navy, #003366);
    font-weight: 700;
}

.filter-chips {
    display: flex;
    align-items: center;
    gap: 0.6rem;
}

.filter-chips-label {
    color: #6c757d;
    font-size: 1.3rem;
}

.filter-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.6rem;
    height: 2.4rem;
    padding: 0 0.9rem;
    border: 1.5px solid #d1d5db;
    border-radius: 999px;
    background-color: #ffffff;
    color: #333333;
    font-size: 1.3rem;
    cursor: pointer;
    transition: border-color 0.2s ease;
}

.filter-chip:hover {
    border-color: var(--bc-navy, #003366);
}

.filter-chip i {
    color: #6c757d;
    font-size: 1.15rem;
}
</style>

<style>
/* The theme's yellow focus ring would sit inside the field; the wrapper's navy
   border (.search-bar-wrapper:focus-within) is the focus indicator instead. */
.sorting-bar-container .search-bar-wrapper input.search-input:focus,
.sorting-bar-container .search-bar-wrapper input.search-input:focus-visible,
.sorting-bar-container .search-bar-wrapper input.search-input:-webkit-autofill,
.sorting-bar-container
    .search-bar-wrapper
    input.search-input:-webkit-autofill:focus {
    outline: none !important;
    border: none !important;
    background-color: #ffffff !important;
    /* Also paints over Chrome's yellow autofill fill, which ignores background. */
    box-shadow: 0 0 0 1000px #ffffff inset !important;
    -webkit-text-fill-color: #333333 !important;
}

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
