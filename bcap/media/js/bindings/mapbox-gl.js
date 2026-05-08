// Overrides arches/arches/app/media/js/bindings/mapbox-gl.js
import ko from 'knockout';
import 'arches/arches/app/media/js/bindings/mapbox-gl';

// We may need to expand this for other colors in the future. Perhaps adding in "pattern-crosshatch-red" etc.
const PATTERN_DEFAULTS = { bgColor: 'rgba(255, 0, 0, 0.15)', lineColor: 'rgba(255, 0, 0, 0.8)' };

const PATTERNS = {
    'pattern-crosshatch': { ...PATTERN_DEFAULTS, draw: (ctx, size) => {
        ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(size, size); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(size, 0); ctx.lineTo(0, size); ctx.stroke();
    }},
    'pattern-vertical': { ...PATTERN_DEFAULTS, draw: (ctx, size) => {
        for (let x = 0; x < size; x += 4) {
            ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, size); ctx.stroke();
        }
    }},
    'pattern-horizontal': { ...PATTERN_DEFAULTS, draw: (ctx, size) => {
        for (let y = 0; y < size; y += 4) {
            ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(size, y); ctx.stroke();
        }
    }},
};

const addPattern = (map, imageId) => {
    const pattern = PATTERNS[imageId];
    if (!pattern || map.hasImage(imageId)) return;
    const size = 16;
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = size;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = pattern.bgColor;
    ctx.fillRect(0, 0, size, size);
    ctx.strokeStyle = pattern.lineColor;
    ctx.lineWidth = 1;
    pattern.draw(ctx, size);
    map.addImage(imageId, ctx.getImageData(0, 0, size, size));
};

// Override arches init
ko.bindingHandlers.mapboxgl.init = ((originalInit) => (element, valueAccessor) => {
    originalInit(element, () => {
        const value = ko.unwrap(valueAccessor());
        const { afterRender } = value;
        return {
            ...value,
            afterRender: (map) => {
                if (typeof afterRender === 'function') afterRender(map);
                console.log('[bcap] mapbox-gl binding loaded');
                map.on('load', () => Object.keys(PATTERNS).forEach(id => addPattern(map, id)));
            },
        };
    });
})(ko.bindingHandlers.mapboxgl.init);

export default ko.bindingHandlers.mapboxgl;
