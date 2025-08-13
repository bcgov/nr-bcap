// vite-shims/chosen-global.js
import $ from 'jquery';

// Make jQuery global for UMD plugins (chosen, etc.)
if (typeof window !== 'undefined') {
  window.$ = window.jQuery = window.jQuery || $;
}

// Now load the real plugin (side-effect import)
import 'chosen-js/chosen.jquery.min.js';

export default $;