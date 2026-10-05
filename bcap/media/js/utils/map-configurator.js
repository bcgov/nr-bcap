import MapboxGl from 'mapbox-gl';
import arches from 'arches';
const _BULB_OFF = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <line x1="9" y1="18" x2="15" y2="18"/><line x1="10" y1="22" x2="14" y2="22"/>
  <path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14"/>
</svg>`;

const _BULB_ON = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="#f59e0b" stroke="#d97706" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <line x1="9" y1="18" x2="15" y2="18"/><line x1="10" y1="22" x2="14" y2="22"/>
  <path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14"/>
</svg>`;

function LayerToggleControl(layerName) {
    let _map;
    let _active = false;
    let _added = false;
    let _btn;

    function _apply() {
        const overlay = arches.mapLayers.find((l) => l.name === layerName);
        if (!overlay) return;

        if (_active && !_added) {
            const firstDrawLayer = _map
                .getStyle()
                .layers.find((l) => l.id.startsWith('gl-draw-'));
            for (const definition of overlay.layer_definitions) {
                _map.addLayer(definition, firstDrawLayer?.id);
            }
            _added = true;
        } else {
            const visibility = _active ? 'visible' : 'none';
            overlay.layer_definitions.forEach(({ id }) => {
                if (_map.getLayer(id))
                    _map.setLayoutProperty(id, 'visibility', visibility);
            });
        }

        if (_btn) {
            _btn.innerHTML = _active ? _BULB_ON : _BULB_OFF;
            _btn.classList.toggle('active', _active);
        }
    }

    return {
        onAdd(map) {
            _map = map;
            _btn = document.createElement('button');
            _btn.className = 'mapboxgl-ctrl-icon';
            _btn.innerHTML = _BULB_OFF;
            _btn.title = layerName;
            _btn.style.cssText =
                'display:flex; align-items:center; justify-content:center; width:29px; height:29px; cursor:pointer; background:none; border:none; padding:0;';

            _btn.addEventListener('click', () => {
                _active = !_active;
                _apply();
            });

            const container = document.createElement('div');
            container.className = 'mapboxgl-ctrl mapboxgl-ctrl-group';
            container.appendChild(_btn);
            return container;
        },
        onRemove() {
            _map = null;
        },
        activate() {
            if (!_active) {
                _active = true;
                _apply();
            }
        },
    };
}

const mapConfigurator = {
    preConfig: function (map) {
        console.log('Custom pre-config');
        console.log('Adding control');
        map.addControl(new MapboxGl.ScaleControl({ maxWidth: 200 }));
    },

    postConfig: function (map) {
        console.log('Custom post-config');
        console.log('layers', arches.layers);
        const siteBoundaryControl = LayerToggleControl(
            'Archaeological Site - Site Boundary',
        );
        map.addControl(siteBoundaryControl, 'top-left');

        map.on('idle', function () {
            if (
                map
                    .getContainer()
                    .closest('.map-widget')
                    ?.classList.contains('archaeological_site') &&
                map._controls.find((c) => c.getMode)?.getAll()?.features
                    ?.length > 0
            ) {
                siteBoundaryControl.activate();
            }
        });

        // Workaround for bug in core causing geocoder placeholder to be null
        // NOTE: map._controls is a private API; may break on Mapbox GL upgrades
        map._controls.forEach((control) => {
            if ('geocoderService' in control && 'placeholder' in control) {
                control.setPlaceholder('Find an address...');
            }
        });
    },
};

export default mapConfigurator;
