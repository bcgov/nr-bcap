import $ from 'jquery';
if (typeof window !== 'undefined') {
  window.$ = window.jQuery = window.jQuery || $;
}

// Use the AMD build so it registers global Dropzone
import 'dropzone/dist/min/dropzone-amd-module.min.js';

const DZ = window.Dropzone;
export default DZ;