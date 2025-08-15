// vite-shims/backbone-global.js
const g = typeof window !== 'undefined' ? window : globalThis;
const bb = g.Backbone;
if (!bb) throw new Error('Global Backbone not found on window');
if (!bb.$ && (g.jQuery || g.$)) bb.$ = g.jQuery || g.$;
export default bb;
