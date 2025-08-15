// e.g. bcap/vite-entries/search.entry.ts
import { createApp } from "vue";
import ArchaeologicalSite from "@/bcap/components/pages/details/ArchaeologicalSite/ArchaeologicalSite.vue";
import "@/bcap/primevue-theme-global.ts";

// Register the KO binding name used in your HTML
window.BCAP.vueKO.register({
    name: "detailsVueComponent",
    createApp,
    component: ArchaeologicalSite,
    source: "vite",
});

// after your BCAP.vueKO.register(...)
window.__BCAP_VITE_READY_FIRED__ = true; // <-- flag for late listeners
document.dispatchEvent(new Event("__BCAP_VITE_READY__")); // <-- event for normal flow

console.log("[BCAP] Vite entry loaded");
if (import.meta.hot) import.meta.hot.accept();
