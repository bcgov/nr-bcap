import MapboxGl from 'mapbox-gl';

const mapConfigurator = {
    preConfig: function (map) {
        console.log('Custom pre-config');
        console.log('Adding control');
        map.addControl(new MapboxGl.ScaleControl({ maxWidth: 200 }));
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

    },
};

export default mapConfigurator;
