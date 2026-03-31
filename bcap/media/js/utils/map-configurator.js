import MapboxGl from 'mapbox-gl';

const ARCH_SITE_GEOM_NODE = 'b18223c2-13ef-11f0-8695-0242ac170007';
const LABEL_LAYER = 'site-polygon-borden-labels';
const PATTERN_FILL_LAYER = 'site-polygon-pattern-fill';

const BRIGHT_RED = 'rgba(255, 0, 0, 0.7)';
const BRIGHT_RED_BORDER = 'rgba(255, 0, 0, 1)';
const PALE_RED = 'rgba(255, 0, 0, 0.3)';
const PALE_RED_BORDER = 'rgba(255, 0, 0, 0.7)';

const PATTERN_STATUSES = ['Legacy', 'Recorded/Unprotected', 'Cancelled Record'];

const STATUS_FILL_EXPRESSION = [
    'match',
    ['coalesce', ['get', 'registration_status'], ''],
    'Registered',
    BRIGHT_RED,
    'Registry Candidate',
    BRIGHT_RED,
    'Decision Pending',
    BRIGHT_RED,
    'Federal Jurisdiction',
    PALE_RED,
    'Legacy',
    'rgba(0, 0, 0, 0)',
    'Recorded/Unprotected',
    'rgba(0, 0, 0, 0)',
    'Cancelled Record',
    'rgba(0, 0, 0, 0)',
    BRIGHT_RED,
];

const STATUS_BORDER_EXPRESSION = [
    'match',
    ['coalesce', ['get', 'registration_status'], ''],
    'Registered',
    BRIGHT_RED_BORDER,
    'Registry Candidate',
    BRIGHT_RED_BORDER,
    'Decision Pending',
    BRIGHT_RED_BORDER,
    'Federal Jurisdiction',
    PALE_RED_BORDER,
    'Legacy',
    BRIGHT_RED_BORDER,
    'Recorded/Unprotected',
    BRIGHT_RED_BORDER,
    'Cancelled Record',
    BRIGHT_RED_BORDER,
    BRIGHT_RED_BORDER,
];

function createPatternImage(size, bgColor, lineColor, drawLines) {
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');

    ctx.fillStyle = bgColor;
    ctx.fillRect(0, 0, size, size);

    ctx.strokeStyle = lineColor;
    ctx.lineWidth = 1.5;
    drawLines(ctx, size);

    return ctx.getImageData(0, 0, size, size);
}

function createCrossHatchPattern() {
    return createPatternImage(
        16,
        'rgba(255, 0, 0, 0.15)',
        'rgba(255, 0, 0, 0.8)',
        (ctx, s) => {
            ctx.beginPath();
            ctx.moveTo(0, 0);
            ctx.lineTo(s, s);
            ctx.moveTo(s, 0);
            ctx.lineTo(0, s);
            ctx.stroke();
        },
    );
}

function createVerticalLinesPattern() {
    return createPatternImage(
        16,
        'rgba(255, 0, 0, 0.15)',
        'rgba(255, 0, 0, 0.8)',
        (ctx, s) => {
            for (let x = 4; x < s; x += 8) {
                ctx.beginPath();
                ctx.moveTo(x, 0);
                ctx.lineTo(x, s);
                ctx.stroke();
            }
        },
    );
}

function createHorizontalLinesPattern() {
    return createPatternImage(
        16,
        'rgba(255, 0, 0, 0.15)',
        'rgba(255, 0, 0, 0.8)',
        (ctx, s) => {
            for (let y = 4; y < s; y += 8) {
                ctx.beginPath();
                ctx.moveTo(0, y);
                ctx.lineTo(s, y);
                ctx.stroke();
            }
        },
    );
}

function findArchSiteLayer(map, prefix) {
    const style = map.getStyle();
    if (!style?.layers) return null;

    return (
        style.layers.find(
            (l) =>
                l.id.startsWith(prefix) &&
                l.id.includes(ARCH_SITE_GEOM_NODE) &&
                !l.id.includes('-click') &&
                !l.id.includes('-hover'),
        ) || null
    );
}

function registerPatterns(map) {
    if (!map.hasImage('pattern-crosshatch')) {
        map.addImage('pattern-crosshatch', createCrossHatchPattern(), {
            sdf: false,
        });
    }

    if (!map.hasImage('pattern-vertical')) {
        map.addImage('pattern-vertical', createVerticalLinesPattern(), {
            sdf: false,
        });
    }

    if (!map.hasImage('pattern-horizontal')) {
        map.addImage('pattern-horizontal', createHorizontalLinesPattern(), {
            sdf: false,
        });
    }
}

function addBordenLabels(map) {
    if (map.getLayer(LABEL_LAYER)) return;

    const fillLayer = findArchSiteLayer(map, 'resources-fill-');
    if (!fillLayer) return;

    const source = fillLayer.source;
    const sourceLayer = fillLayer['source-layer'] || ARCH_SITE_GEOM_NODE;

    map.addLayer({
        id: LABEL_LAYER,
        type: 'symbol',
        source: source,
        'source-layer': sourceLayer,
        layout: {
            'text-field': ['coalesce', ['get', 'borden_number'], ''],
            'text-size': 12,
            'text-font': ['Open Sans Bold', 'Arial Unicode MS Bold'],
            'text-allow-overlap': false,
            'text-ignore-placement': false,
        },
        paint: {
            'text-color': '#333333',
            'text-halo-color': 'rgba(255, 255, 255, 0.9)',
            'text-halo-width': 1.5,
        },
    });
}

function applyStatusStyling(map) {
    const fillLayer = findArchSiteLayer(map, 'resources-fill-');
    const lineLayer = findArchSiteLayer(map, 'resources-line-');
    if (!fillLayer) return;

    const source = fillLayer.source;
    const sourceLayer = fillLayer['source-layer'] || ARCH_SITE_GEOM_NODE;

    map.setPaintProperty(fillLayer.id, 'fill-color', STATUS_FILL_EXPRESSION);

    if (!map.getLayer(PATTERN_FILL_LAYER)) {
        map.addLayer(
            {
                id: PATTERN_FILL_LAYER,
                type: 'fill',
                source: source,
                'source-layer': sourceLayer,
                filter: [
                    'in',
                    ['get', 'registration_status'],
                    ['literal', PATTERN_STATUSES],
                ],
                paint: {
                    'fill-pattern': [
                        'match',
                        ['get', 'registration_status'],
                        'Legacy',
                        'pattern-crosshatch',
                        'Recorded/Unprotected',
                        'pattern-vertical',
                        'Cancelled Record',
                        'pattern-horizontal',
                        'pattern-horizontal',
                    ],
                },
            },
            fillLayer.id,
        );
    }

    if (lineLayer) {
        map.setPaintProperty(
            lineLayer.id,
            'line-color',
            STATUS_BORDER_EXPRESSION,
        );
    }
}

function applySearchMapStyling(map) {
    registerPatterns(map);
    addBordenLabels(map);
    applyStatusStyling(map);
}

const mapConfigurator = {
    /* Can tell which context we are in by the following. In each case, we are in that context if the search returns
            an object
            Search map: map.getCanvasContainer().closest("section.search-map-container")
            Map Header: map.getCanvasContainer().closest("div.report-map-header-component")
            Map Editor: map.getCanvasContainer().closest("div.map-widget")
        */
    icons: [],
    /*
        icons: [{"name":"micro-marker", "url":'/int/bc-fossil-management/files/media/img/markers/micro.png'},
            {"name":"macro-marker", "url":'/int/bc-fossil-management/files/media/img/markers/macro.png'},
            {"name":"macromicro-marker", "url":'/int/bc-fossil-management/files/media/img/markers/macromicro.png'},
        ],
         */

    preConfig: function (map) {
        console.log('Custom pre-config');
        console.log('Adding control');
        map.addControl(new MapboxGl.ScaleControl({ maxWidth: 200 }));
        this.icons.forEach((icon) => {
            console.log(`Loading ${icon.name}: ${icon.url}`);
            map.loadImage(icon.url, (error, image) => {
                if (error) {
                    console.error(`Failed to load icon ${icon.name}:`, error);
                    return;
                }
                map.addImage(icon.name, image);
            });
        });
    },

    postConfig: function (map) {
        console.log('Custom post-config');
        // Workaround for bug in core causing geocoder placeholder to be null
        // NOTE: map._controls is a private API; may break on Mapbox GL upgrades
        map._controls.forEach((control) => {
            if ('geocoderService' in control && 'placeholder' in control) {
                control.setPlaceholder('Find an address...');
            }
        });

        const isSearchMap = map
            .getCanvasContainer()
            .closest('section.search-map-container');
        if (isSearchMap) {
            if (map.isStyleLoaded()) {
                applySearchMapStyling(map);
            } else {
                map.once('idle', () => applySearchMapStyling(map));
            }
        }
    },
};

export default mapConfigurator;
