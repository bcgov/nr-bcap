// src/shims/maplibre-gl-shim.ts
// ESM facade that guarantees maplibregl is available at import time.
// If window.maplibregl isn't ready yet, we dynamically load the UMD and then export it.

// Types (erased at runtime, you still get IntelliSense)
export type {
    Map as MapLibreMap,
    NavigationControl as MapLibreNavigationControl,
    ScaleControl as MapLibreScaleControl,
    AttributionControl as MapLibreAttributionControl,
    Marker as MapLibreMarker,
    Popup as MapLibrePopup,
} from "maplibre-gl";

const g: any = typeof window !== "undefined" ? window : globalThis;

// Already there? Great — export immediately.
let m: any = (g as any).maplibregl;

if (!m) {
    // DEV uses /@fs path; PROD uses emitted /vendor asset (from your Vite plugin).
    await import(
        "/@fs/web_root/bcap/node_modules/maplibre-gl/dist/maplibre-gl.js?module"
    );

    m = (g as any).maplibregl;
    if (!m) {
        throw new Error(
            "[maplibre-gl-shim] Failed to initialize MapLibre GL (window.maplibregl not found after UMD load).",
        );
    }
}

// Make sure the global is set (defensive)
(g as any).maplibregl = m;

// Default + named exports so "import maplibregl from 'maplibre-gl'" works
export default m;
export const Map = m.Map;
export const NavigationControl = m.NavigationControl;
export const ScaleControl = m.ScaleControl;
export const AttributionControl = m.AttributionControl;
export const Marker = m.Marker;
export const Popup = m.Popup;
