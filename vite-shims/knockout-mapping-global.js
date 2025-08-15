// vite-shims/knockout-mapping-global.js
const g = typeof window !== 'undefined' ? window : globalThis;
const mapping = g.ko && (g.ko.mapping || (g.ko.plugins && g.ko.plugins.mapping));
if (!mapping) throw new Error('Global knockout-mapping not found on window');
export default mapping;
