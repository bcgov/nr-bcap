import $ from 'jquery';
import _ from 'underscore';
import ko from 'knockout';
import koMapping from 'knockout-mapping';
import slick from 'slick';
import arches from 'arches';
import MapReportViewModel from 'viewmodels/map-report';
import chosen from 'bindings/chosen';
import uuid from 'uuid';
import geojsonExtent from 'geojson-extent';
import geojsonhint from 'geojsonhint';
import { kml } from 'togeojson';
import shp from 'shpjsesm';
import proj4 from 'proj4';
import MapboxDraw from 'mapbox-gl-draw';
import MapComponentViewModel from 'views/components/map';
import selectFeatureLayersFactory from 'views/components/cards/select-feature-layers';
import geojsonDatatype from 'views/components/datatypes/geojson-feature-collection';
import externalUtils from 'utils/map-filter-utils';

// Common projected coordinate systems used in BC/Western Canada.
//
// Reference:
//     BC FSP Electronic Submission Format, Data Types Overview
//         - (www.for.gov.bc.ca/his/fsp/webhelp/FSP/Online_Tech_Specs/PDFs/FSP_ESF_2-6_Overview__Data_Types.pdf)
//     Proj4 strings sourced from epsg.io.
//
// These are registered with proj4 so we can transform coordinates when a
// user uploads a bare .shp file without an accompanying .prj. When a .prj
// is provided it is passed directly to shpjs which handles reprojection
// automatically.
var PROJECTIONS = {
    WGS84: 'EPSG:4326',
    BC_ALBERS: 'EPSG:3005',
    NAD83_UTM_7N: 'EPSG:26907',
    NAD83_UTM_8N: 'EPSG:26908',
    NAD83_UTM_9N: 'EPSG:26909',
    NAD83_UTM_10N: 'EPSG:26910',
    NAD83_UTM_11N: 'EPSG:26911',
    WGS84_UTM_7N: 'EPSG:32607',
    WGS84_UTM_8N: 'EPSG:32608',
    WGS84_UTM_9N: 'EPSG:32609',
    WGS84_UTM_10N: 'EPSG:32610',
    WGS84_UTM_11N: 'EPSG:32611',
};

proj4.defs(
    PROJECTIONS.BC_ALBERS,
    '+proj=aea +lat_1=50 +lat_2=58.5 +lat_0=45 +lon_0=-126 +x_0=1000000 +y_0=0 +datum=NAD83 +units=m +no_defs',
);
proj4.defs(
    PROJECTIONS.NAD83_UTM_7N,
    '+proj=utm +zone=7 +datum=NAD83 +units=m +no_defs',
);
proj4.defs(
    PROJECTIONS.NAD83_UTM_8N,
    '+proj=utm +zone=8 +datum=NAD83 +units=m +no_defs',
);
proj4.defs(
    PROJECTIONS.NAD83_UTM_9N,
    '+proj=utm +zone=9 +datum=NAD83 +units=m +no_defs',
);
proj4.defs(
    PROJECTIONS.NAD83_UTM_10N,
    '+proj=utm +zone=10 +datum=NAD83 +units=m +no_defs',
);
proj4.defs(
    PROJECTIONS.NAD83_UTM_11N,
    '+proj=utm +zone=11 +datum=NAD83 +units=m +no_defs',
);
proj4.defs(
    PROJECTIONS.WGS84_UTM_7N,
    '+proj=utm +zone=7 +datum=WGS84 +units=m +no_defs',
);
proj4.defs(
    PROJECTIONS.WGS84_UTM_8N,
    '+proj=utm +zone=8 +datum=WGS84 +units=m +no_defs',
);
proj4.defs(
    PROJECTIONS.WGS84_UTM_9N,
    '+proj=utm +zone=9 +datum=WGS84 +units=m +no_defs',
);
proj4.defs(
    PROJECTIONS.WGS84_UTM_10N,
    '+proj=utm +zone=10 +datum=WGS84 +units=m +no_defs',
);
proj4.defs(
    PROJECTIONS.WGS84_UTM_11N,
    '+proj=utm +zone=11 +datum=WGS84 +units=m +no_defs',
);

// Check whether any coordinates in a FeatureCollection fall outside valid
// WGS84 lng/lat bounds, which indicates the data is still in a projected
// coordinate system and needs reprojection before Mapbox can display it.
var needsReprojection = function (geoJSON) {
    var checked = 0;
    var outOfBounds = 0;
    var walkCoords = function (coords) {
        if (typeof coords[0] === 'number') {
            checked++;
            if (
                coords[0] < -180 ||
                coords[0] > 180 ||
                coords[1] < -90 ||
                coords[1] > 90
            ) {
                outOfBounds++;
            }
            return;
        }
        for (var i = 0; i < coords.length; i++) {
            walkCoords(coords[i]);
        }
    };
    if (geoJSON && geoJSON.features) {
        for (var i = 0; i < geoJSON.features.length; i++) {
            var geom = geoJSON.features[i].geometry;
            if (geom && geom.coordinates) {
                walkCoords(geom.coordinates);
            }
        }
    }
    return checked > 0 && outOfBounds / checked > 0.5;
};

// Transform all coordinates in a FeatureCollection in-place from sourceCRS
// to WGS84. It is used as a fallback when shpjs could not reproject (i.e., no
// .prj was available).
var reprojectGeoJSON = function (geoJSON, sourceCRS) {
    var transformCoords = function (coords) {
        if (typeof coords[0] === 'number') {
            var transformed = proj4(sourceCRS, PROJECTIONS.WGS84, [
                coords[0],
                coords[1],
            ]);
            coords[0] = transformed[0];
            coords[1] = transformed[1];
            return;
        }
        for (var i = 0; i < coords.length; i++) {
            transformCoords(coords[i]);
        }
    };
    if (geoJSON && geoJSON.features) {
        for (var i = 0; i < geoJSON.features.length; i++) {
            var geom = geoJSON.features[i].geometry;
            if (geom && geom.coordinates) {
                transformCoords(geom.coordinates);
            }
        }
    }
    return geoJSON;
};

// Attempt to guess the source projection from coordinate ranges when no .prj
// file is available. This is specific to BC/Western Canada — BC Albers
// (EPSG:3005) coordinates have large x values around 1,000,000 and y values
// under ~1,200,000, while UTM coordinates have y values in the 5–7 million
// range. It defaults to EPSG:3005 (BC Albers) as it is the most common
// projection used by the BC government.
var guessProjectionFromCoords = function (geoJSON) {
    var sample = null;
    if (geoJSON && geoJSON.features && geoJSON.features.length > 0) {
        var geom = geoJSON.features[0].geometry;
        if (geom && geom.coordinates) {
            var coords = geom.coordinates;
            while (Array.isArray(coords[0])) {
                coords = coords[0];
            }
            sample = coords;
        }
    }
    if (!sample) return PROJECTIONS.BC_ALBERS;
    var x = sample[0];
    var y = sample[1];
    if (x > 200000 && x < 1900000 && y > 0 && y < 1200000) {
        return PROJECTIONS.BC_ALBERS;
    }
    if (x > 100000 && x < 900000 && y > 5000000 && y < 7000000) {
        if (x < 500000) {
            return PROJECTIONS.NAD83_UTM_10N;
        }
        return PROJECTIONS.NAD83_UTM_9N;
    }
    return PROJECTIONS.BC_ALBERS;
};

var MapEditorViewModel = function (params) {
    var self = this;
    var padding = 40;
    var drawFeatures;

    var resourceId = params.tile ? params.tile.resourceinstance_id : '';
    if (this.widgets === undefined) {
        // could be [], so checking specifically for undefined
        this.widgets = params.widgets || [];
    }

    this.geojsonWidgets = this.widgets.filter(function (widget) {
        return widget.datatype.datatype === 'geojson-feature-collection';
    });
    this.newNodeId = null;
    this.featureLookup = {};
    this.selectedFeatureIds = ko.observableArray();
    this.geoJSONString = ko.observable();
    this.draw = null;
    this.selectSource = this.selectSource || ko.observable();
    this.selectSourceLayer = this.selectSourceLayer || ko.observable();
    this.drawAvailable = ko.observable(false);
    this.bufferNodeId = ko.observable();
    this.bufferDistance = ko.observable(0);
    this.bufferUnits = ko.observable('m');
    this.bufferResult = ko.observable();
    this.bufferAddNew = ko.observable(false);
    this.allowAddNew =
        this.card && this.card.canAdd() && this.tile !== this.card.newTile;
    this.selectText = ko.observable('Copy geometry');

    var selectSource = this.selectSource();
    var selectSourceLayer = this.selectSourceLayer();
    var selectFeatureLayers = selectFeatureLayersFactory(
        resourceId,
        selectSource,
        selectSourceLayer,
    );

    this.setSelectLayersVisibility = function (visibility) {
        var map = self.map();
        if (map) {
            selectFeatureLayers.forEach(function (layer) {
                map.setLayoutProperty(
                    layer.id,
                    'visibility',
                    visibility ? 'visible' : 'none',
                );
            });
        }
    };

    var sources = [];
    for (var sourceName in arches.mapSources) {
        if (
            Object.prototype.hasOwnProperty.call(arches.mapSources, sourceName)
        ) {
            sources.push(sourceName);
        }
    }
    var updateSelectLayers = function () {
        var source = self.selectSource();
        var sourceLayer = self.selectSourceLayer();
        selectFeatureLayers =
            sources.indexOf(source) > 0
                ? selectFeatureLayersFactory(resourceId, source, sourceLayer)
                : [];
        self.additionalLayers(
            extendedLayers.concat(selectFeatureLayers, geojsonLayers),
        );
    };
    this.selectSource.subscribe(updateSelectLayers);
    this.selectSourceLayer.subscribe(updateSelectLayers);

    this.setDrawTool = function (tool) {
        var showSelectLayers = tool === 'select_feature';
        self.setSelectLayersVisibility(showSelectLayers);
        if (showSelectLayers) {
            self.draw.changeMode('simple_select');
            self.selectedFeatureIds([]);
        } else {
            if (tool) {
                self.draw.changeMode(tool);
                self.map().draw_mode = tool;
            }
        }
    };

    self.geojsonWidgets.forEach(function (widget) {
        var id = ko.unwrap(widget.node_id);
        self.featureLookup[id] = {
            features: ko.computed(function () {
                var value = koMapping.toJS(self.tile.data[id]);
                if (value) return value.features;
                else return [];
            }),
            selectedTool: ko.observable(),
            dropErrors: ko.observableArray(),
        };
        self.featureLookup[id].selectedTool.subscribe(function (tool) {
            if (self.draw) {
                if (tool === '') {
                    self.draw.trash();
                    self.draw.changeMode('simple_select');
                } else if (tool) {
                    _.each(self.featureLookup, function (value, key) {
                        if (key !== id) {
                            value.selectedTool(null);
                        }
                    });
                    self.newNodeId = id;
                }
                self.setDrawTool(tool);
            }
        });
    });

    this.selectedTool = ko.pureComputed(function () {
        var tool;
        _.find(self.featureLookup, function (value) {
            var selectedTool = value.selectedTool();
            if (selectedTool) tool = selectedTool;
        });
        return tool;
    });

    this.updateTiles = function () {
        var featureCollection = self.draw.getAll();
        _.each(self.featureLookup, function (value) {
            value.selectedTool(null);
        });
        self.geojsonWidgets.forEach(function (widget) {
            var id = ko.unwrap(widget.node_id);
            var features = [];
            featureCollection.features.forEach(function (feature) {
                if (feature.properties.nodeId === id) features.push(feature);
            });
            if (ko.isObservable(self.tile.data[id])) {
                self.tile.data[id]({
                    type: 'FeatureCollection',
                    features: features,
                });
            } else {
                if (self.tile.data[id]) {
                    self.tile.data[id].features(features);
                }
            }
        });
    };

    var getDrawFeatures = function () {
        var drawFeatures = [];
        self.geojsonWidgets.forEach(function (widget) {
            var id = ko.unwrap(widget.node_id);
            var featureCollection = koMapping.toJS(self.tile.data[id]);
            if (featureCollection) {
                featureCollection.features.forEach(function (feature) {
                    if (!feature.id) {
                        feature.id = uuid.generate();
                    }
                    feature.properties.nodeId = id;
                });
                drawFeatures = drawFeatures.concat(featureCollection.features);
            }
        });
        return drawFeatures;
    };
    drawFeatures = getDrawFeatures();

    if (drawFeatures.length > 0) {
        params.usePosition = false;
        params.bounds = geojsonExtent({
            type: 'FeatureCollection',
            features: drawFeatures,
        });
        params.fitBoundsOptions = {
            padding: {
                top: padding,
                left: padding + 200,
                bottom: padding,
                right: padding + 200,
            },
        };
    }

    params.activeTab = 'editor';
    params.sources = Object.assign(
        {
            'geojson-editor-data': {
                type: 'geojson',
                data: {
                    type: 'FeatureCollection',
                    features: [],
                },
            },
        },
        params.sources,
    );
    var extendedLayers = [];
    if (params.layers) {
        extendedLayers = ko.unwrap(params.layers);
    }
    var geojsonLayers = [
        {
            id: 'geojson-editor-polygon-fill',
            type: 'fill',
            filter: ['==', '$type', 'Polygon'],
            paint: {
                'fill-color': '#3bb2d0',
                'fill-outline-color': '#3bb2d0',
                'fill-opacity': 0.1,
            },
            source: 'geojson-editor-data',
        },
        {
            id: 'geojson-editor-polygon-stroke-base',
            type: 'line',
            filter: ['==', '$type', 'Polygon'],
            layout: {
                'line-cap': 'round',
                'line-join': 'round',
            },
            paint: {
                'line-color': '#fff',
                'line-width': 4,
            },
            source: 'geojson-editor-data',
        },
        {
            id: 'geojson-editor-polygon-stroke',
            type: 'line',
            filter: ['==', '$type', 'Polygon'],
            layout: {
                'line-cap': 'round',
                'line-join': 'round',
            },
            paint: {
                'line-color': '#3bb2d0',
                'line-width': 2,
            },
            source: 'geojson-editor-data',
        },
        {
            id: 'geojson-editor-line',
            type: 'line',
            filter: ['==', '$type', 'LineString'],
            layout: {
                'line-cap': 'round',
                'line-join': 'round',
            },
            paint: {
                'line-color': '#3bb2d0',
                'line-width': 2,
            },
            source: 'geojson-editor-data',
        },
        {
            id: 'geojson-editor-point-point-stroke',
            type: 'circle',
            filter: ['==', '$type', 'Point'],
            paint: {
                'circle-radius': 6,
                'circle-opacity': 1,
                'circle-color': '#fff',
            },
            source: 'geojson-editor-data',
        },
        {
            id: 'geojson-editor-point',
            type: 'circle',
            filter: ['==', '$type', 'Point'],
            paint: {
                'circle-radius': 5,
                'circle-color': '#3bb2d0',
            },
            source: 'geojson-editor-data',
        },
    ];

    params.layers = ko.observable(
        extendedLayers.concat(selectFeatureLayers, geojsonLayers),
    );

    MapComponentViewModel.apply(this, [params]);

    this.deleteFeature = function (feature) {
        if (self.draw) {
            self.draw.delete(feature.id);
            self.selectedFeatureIds(
                self.selectedFeatureIds().filter(function (id) {
                    return id !== feature.id;
                }),
            );
            self.updateTiles();
        }
    };

    this.editFeature = function (feature) {
        if (self.draw) {
            self.draw.changeMode('simple_select', {
                featureIds: [feature.id],
            });
            self.selectedFeatureIds([feature.id]);
            _.each(self.featureLookup, function (value) {
                value.selectedTool(null);
            });
        }
    };

    this.updateLayers = function (layers) {
        var map = self.map();
        var style = map.getStyle();
        if (style) {
            style.layers = self.draw
                ? layers.concat(self.draw.options.styles)
                : layers;
            map.setStyle(style);
        }
    };

    this.fitFeatures = function (features) {
        var map = self.map();
        var bounds = geojsonExtent({
            type: 'FeatureCollection',
            features: features,
        });
        var camera = map.cameraForBounds(bounds, { padding: padding });
        map.jumpTo(camera);
    };

    this.editGeoJSON = function (features, nodeId) {
        var geoJSONString = JSON.stringify(
            {
                type: 'FeatureCollection',
                features: features,
            },
            null,
            '   ',
        );
        this.geoJSONString(geoJSONString);
        self.newNodeId = nodeId;
    };
    this.geoJSONString.subscribe(function (geoJSONString) {
        var map = self.map();
        if (geoJSONString === undefined) {
            setupDraw(map);
        } else if (self.draw) {
            map.removeControl(self.draw);
            self.draw = undefined;
            self.selectedFeatureIds([]);
        }
        self.setSelectLayersVisibility(false);
    });
    this.geoJSONErrors = ko
        .pureComputed(function () {
            var geoJSONString = self.geoJSONString();
            var hint = geojsonhint.hint(geoJSONString);
            var errors = [];
            hint.forEach(function (item) {
                if (item.level !== 'message') {
                    errors.push(item);
                }
            });
            return errors;
        })
        .extend({ rateLimit: 50 });
    var geoJSONLayerData = ko
        .pureComputed(function () {
            var geoJSONString = self.geoJSONString();
            var geoJSONErrors = self.geoJSONErrors();
            if (geoJSONErrors.length === 0) return JSON.parse(geoJSONString);
            var fc = {
                type: 'FeatureCollection',
                features: [],
            };
            if (self.bufferNodeId() && self.bufferResult()) {
                fc.features.push(self.bufferResult());
            }
            return fc;
        })
        .extend({ rateLimit: 100 });
    geoJSONLayerData.subscribe(function (data) {
        var map = self.map();
        map.getSource('geojson-editor-data').setData(data);
    });
    this.updateGeoJSON = function () {
        if (self.geoJSONErrors().length === 0) {
            var geoJSON = JSON.parse(this.geoJSONString());
            geoJSON.features.forEach(function (feature) {
                feature.id = uuid.generate();
                if (!feature.properties) feature.properties = {};
                feature.properties.nodeId = self.newNodeId;
            });
            if (ko.isObservable(self.tile.data[self.newNodeId])) {
                self.tile.data[self.newNodeId](geoJSON);
            } else {
                self.tile.data[self.newNodeId].features(geoJSON.features);
            }
            self.geoJSONString(undefined);
        }
    };

    var setupDraw = function (map) {
        var modes = MapboxDraw.modes;
        modes.static = {
            onSetup: function () {
                this.setActionableState();
                return {};
            },
            toDisplayFeatures: function (state, geojson, display) {
                display(geojson);
            },
        };
        self.draw = new MapboxDraw({
            displayControlsDefault: false,
            modes: modes,
            controls: {
                trash: true,
                combine_features: true,
            },
        });
        map.addControl(self.draw);
        self.draw.set({
            type: 'FeatureCollection',
            features: getDrawFeatures(),
        });
        map.on('draw.create', function (e) {
            e.features.forEach(function (feature) {
                self.draw.setFeatureProperty(
                    feature.id,
                    'nodeId',
                    self.newNodeId,
                );
            });
            self.updateTiles();
        });
        map.on('draw.update', function () {
            self.updateTiles();
            if (self.coordinateEditing()) {
                var editingFeature = self.draw.getSelected().features[0];
                if (editingFeature)
                    updateCoordinatesFromFeature(editingFeature);
            }
            if (self.bufferNodeId()) self.updateBufferFeature();
        });
        map.on('draw.delete', self.updateTiles);
        map.on('draw.modechange', function (e) {
            self.updateTiles();
            self.setSelectLayersVisibility(false);
            map.draw_mode = e.mode;
        });
        map.on('draw.selectionchange', function (e) {
            self.selectedFeatureIds(
                e.features.map(function (feature) {
                    return feature.id;
                }),
            );
            if (e.features.length > 0) {
                _.each(self.featureLookup, function (value) {
                    value.selectedTool(null);
                });
            }
            self.setSelectLayersVisibility(false);
        });

        if (self.form)
            self.form.on('tile-reset', function () {
                var style = self.map().getStyle();
                if (style) {
                    self.draw.set({
                        type: 'FeatureCollection',
                        features: getDrawFeatures(),
                    });
                }
                _.each(self.featureLookup, function (value) {
                    if (value.selectedTool()) value.selectedTool('');
                });
            });
        if (self.draw) {
            self.drawAvailable(true);
        }
    };

    if (this.provisionalTileViewModel) {
        this.provisionalTileViewModel.resetAuthoritative();
        this.provisionalTileViewModel.selectedProvisionalEdit.subscribe(
            function (val) {
                if (val) {
                    var displayAll = function () {
                        var featureCollection;
                        for (var k in self.tile.data) {
                            if (self.featureLookup[k] && self.draw) {
                                try {
                                    featureCollection = self.draw.getAll();
                                    featureCollection.features = ko.unwrap(
                                        self.featureLookup[k].features,
                                    );
                                    self.draw.set(featureCollection);
                                } catch (e) {
                                    //pass: TypeError in draw seems inconsequential.
                                }
                            }
                        }
                    };
                    setTimeout(displayAll, 100);
                }
            },
        );
    }

    this.map.subscribe(setupDraw);

    self.map.subscribe(function (map) {
        if (self.draw && !params.draw) {
            params.draw = self.draw;
        }
        if (map && !params.map) {
            params.map = map;
        }
    });

    if (!params.additionalDrawOptions) {
        params.additionalDrawOptions = [];
    }

    self.geojsonWidgets.forEach(function (widget) {
        if (widget.config.geometryTypes) {
            widget.drawTools = ko.pureComputed(function () {
                var options = [
                    {
                        value: '',
                        text: '',
                    },
                ];
                options = options.concat(
                    ko.unwrap(widget.config.geometryTypes).map(function (type) {
                        var option = {};
                        switch (ko.unwrap(type.id)) {
                            case 'Point':
                                option.value = 'draw_point';
                                option.text = arches.translations.mapAddPoint;
                                break;
                            case 'Line':
                                option.value = 'draw_line_string';
                                option.text = arches.translations.mapAddLine;
                                break;
                            case 'Polygon':
                                option.value = 'draw_polygon';
                                option.text = arches.translations.mapAddPolygon;
                                break;
                            case 'Feature':
                                option.value = 'select_feature';
                                option.text = 'Select Cadastral Feature';
                                break;
                        }
                        return option;
                    }),
                );
                if (self.selectSource()) {
                    options.push({
                        value: 'select_feature',
                        text:
                            self.selectText() ||
                            arches.translations.mapSelectDrawing,
                    });
                }
                options = options.concat(params.additionalDrawOptions);
                return options;
            });
        }
    });

    this.isFeatureClickable = function (feature) {
        var tool = self.selectedTool();
        if (tool && tool !== 'select_feature') return false;
        return (
            feature.properties.resourceinstanceid || self.isSelectable(feature)
        );
    };

    self.isSelectable = function (feature) {
        var selectLayerIds = selectFeatureLayers.map(function (layer) {
            return layer.id;
        });
        return selectLayerIds.indexOf(feature.layer.id) >= 0;
    };

    var addSelectFeatures = function (features) {
        var featureIds = [];
        features.forEach(function (feature) {
            feature.id = uuid.generate();
            feature.properties = {
                nodeId: self.newNodeId,
            };
            self.draw.add(feature);
            featureIds.push(feature.id);
        });
        self.updateTiles();
        if (self.popup) self.popup.remove();
        self.draw.changeMode('simple_select', {
            featureIds: featureIds,
        });
        self.selectedFeatureIds(featureIds);
        _.each(self.featureLookup, function (value) {
            value.selectedTool(null);
        });
    };

    self.selectFeature = function (feature) {
        try {
            let geometry = feature.toJSON().geometry;
            var newFeature = {
                type: 'Feature',
                properties: {},
                geometry: geometry,
            };
            addSelectFeatures([newFeature]);
        } catch (e) {
            $.getJSON(feature.properties.geojson, function (data) {
                addSelectFeatures(data.features);
            });
        }
    };

    self.showSelectFeatureAsSource = function (feature) {
        if (self.selectedTool && self.selectedTool() === 'select_feature')
            return true;
        return false;
    };

    self.selectFeatureAsSource = function (feature) {
        console.log(feature);
        var myfeature = externalUtils.getFeatureFromWFS(
            feature,
            'WHSE_CADASTRE.PMBC_PARCEL_FABRIC_POLY_SVW',
        );
        addSelectFeatures([myfeature]);
    };

    var addFromGeoJSON = function (geoJSONString, nodeId) {
        var hint = geojsonhint.hint(geoJSONString);
        var errors = [];
        hint.forEach(function (item) {
            if (item.level !== 'message') {
                errors.push(item);
            }
        });
        if (errors.length === 0) {
            var geoJSON = JSON.parse(geoJSONString);
            geoJSON.features = geoJSON.features.filter(function (feature) {
                return feature.geometry;
            });
            if (geoJSON.features.length > 0) {
                self.map().fitBounds(geojsonExtent(geoJSON), {
                    padding: padding,
                });
                geoJSON.features.forEach(function (feature) {
                    feature.id = uuid.generate();
                    if (!feature.properties) feature.properties = {};
                    feature.properties.nodeId = nodeId;
                    self.draw.add(feature);
                });
                self.updateTiles();
            }
        }
        return errors;
    };

    self.handleFiles = function (files, nodeId) {
        var errors = [];
        var promises = [];
        // Collect the .prj contents (if provided) so we can pass it to shpjs
        // for reprojection or use it in our fallback reprojection logic.
        var prjString = null;

        // First pass: read the .prj file if one was included alongside the .shp
        for (var i = 0; i < files.length; i++) {
            var extension = files[i].name.split('.').pop().toLowerCase();
            if (extension === 'prj') {
                (function (file) {
                    promises.push(
                        new Promise(function (resolve) {
                            var reader = new window.FileReader();
                            reader.onload = function (e) {
                                prjString = e.target.result;
                                resolve(null);
                            };
                            reader.readAsText(file);
                        }),
                    );
                })(files[i]);
            }
        }

        // Second pass: read the actual geo files. Some companion shapefile
        // extensions (.dbf, .shx, .cpg, .qpj, .prj) are silently ignored
        // so they don't produce "unsupported file" errors when users drag
        // in the full shapefile bundle.
        for (var i = 0; i < files.length; i++) {
            var extension = files[i].name.split('.').pop().toLowerCase();
            if (
                ![
                    'kml',
                    'json',
                    'geojson',
                    'shp',
                    'zip',
                    'prj',
                    'dbf',
                    'shx',
                    'cpg',
                    'qpj',
                ].includes(extension)
            ) {
                errors.push({
                    message: 'File unsupported: "' + files[i].name + '"',
                });
            } else if (
                ['kml', 'json', 'geojson', 'shp', 'zip'].includes(extension)
            ) {
                promises.push(
                    new Promise(function (resolve) {
                        var file = files[i];
                        var extension = file.name
                            .split('.')
                            .pop()
                            .toLowerCase();
                        var reader = new window.FileReader();
                        reader.onload = function (e) {
                            var geoJSON;
                            if (['json', 'geojson'].includes(extension))
                                geoJSON = JSON.parse(e.target.result);
                            else if (extension === 'kml')
                                geoJSON = kml(
                                    new window.DOMParser().parseFromString(
                                        e.target.result,
                                        'text/xml',
                                    ),
                                );
                            // Pass the .prj string to shpjs when available so
                            // it can handle reprojection automatically.
                            else if (extension === 'shp')
                                shp({
                                    shp: e.target.result,
                                    prj: prjString,
                                }).then((parsedShp) => {
                                    resolve(parsedShp);
                                });
                            else if (extension === 'zip')
                                shp(e.target.result).then(function (parsedZip) {
                                    resolve(parsedZip);
                                });
                            if (!['shp', 'zip'].includes(extension))
                                resolve(geoJSON);
                        };
                        if (['shp', 'zip'].includes(extension))
                            reader.readAsArrayBuffer(file);
                        else reader.readAsText(file);
                    }),
                );
            }
        }
        Promise.all(promises).then(function (results) {
            var geoJSON = {
                type: 'FeatureCollection',
                features: results.reduce(function (features, geoJSON) {
                    if (geoJSON && geoJSON.features) {
                        features = features.concat(geoJSON.features);
                    }
                    return features;
                }, []),
            };

            // Fallback reprojection: if coordinates are still outside valid
            // WGS84 bounds (e.g., bare .shp with no .prj or shpjs could not
            // parse the .prj), attempt to reproject using coordinate-range
            // heuristics for common BC/Western Canada projections.
            if (needsReprojection(geoJSON)) {
                var sourceCRS = guessProjectionFromCoords(geoJSON);
                console.warn(
                    'Shapefile coordinates are not in WGS84. ' +
                        'Attempting reprojection from: ' +
                        sourceCRS,
                );
                reprojectGeoJSON(geoJSON, sourceCRS);
            }

            errors = errors.concat(
                addFromGeoJSON(JSON.stringify(geoJSON), nodeId),
            );
            self.featureLookup[nodeId].dropErrors(errors);
        });
    };

    self.dropZoneHandler = function (data, e) {
        var nodeId = data.node.nodeid;
        e.stopPropagation();
        e.preventDefault();
        var files = e.originalEvent.dataTransfer.files;
        self.handleFiles(files, nodeId);
        self.dropZoneLeaveHandler(data, e);
    };

    self.dropZoneOverHandler = function (data, e) {
        e.stopPropagation();
        e.preventDefault();
        e.originalEvent.dataTransfer.dropEffect = 'copy';
    };

    self.dropZoneClickHandler = function (data, e) {
        var fileInput = e.target.parentNode.parentNode.querySelector(
            '.hidden-file-input input',
        );
        var event = window.document.createEvent('MouseEvents');
        event.initEvent('click', true, false);
        fileInput.dispatchEvent(event);
    };

    self.dropZoneEnterHandler = function (data, e) {
        e.target.classList.add('drag-hover');
    };

    self.dropZoneLeaveHandler = function (data, e) {
        e.target.classList.remove('drag-hover');
    };

    self.dropZoneFileSelected = function (data, e) {
        self.handleFiles(e.target.files, data.node.nodeid);
    };
    self.coordinateReferences = arches.preferredCoordinateSystems;
    self.selectedCoordinateReference = ko.observable(
        self.coordinateReferences[0].proj4,
    );
    self.coordinates = ko.observableArray();
    var geographic = '+proj=longlat +datum=WGS84 +no_defs", "default';
    self.rawCoordinates = ko
        .computed(function () {
            return self.coordinates().map(function (coords) {
                var sourceCRS = self.selectedCoordinateReference();
                return proj4(sourceCRS, geographic, [
                    Number(coords[0]()),
                    Number(coords[1]()),
                ]);
            });
        })
        .extend({ throttle: 100 });
    self.rawCoordinates.subscribe(function (rawCoordinates) {
        var selectedFeatureId = self.selectedFeatureIds()[0];
        if (self.coordinateEditing()) {
            if (selectedFeatureId) {
                var drawFeatures = getDrawFeatures();
                drawFeatures.forEach(function (feature) {
                    if (feature.id === selectedFeatureId) {
                        if (feature.geometry.type === 'Polygon') {
                            rawCoordinates.push(rawCoordinates[0]);
                            feature.geometry.coordinates[0] = rawCoordinates;
                        } else if (feature.geometry.type === 'Point')
                            feature.geometry.coordinates = rawCoordinates[0];
                        else feature.geometry.coordinates = rawCoordinates;
                    }
                });
                self.draw.set({
                    type: 'FeatureCollection',
                    features: drawFeatures,
                });
                self.updateTiles();
            } else if (rawCoordinates.length >= self.minCoordinates()) {
                var coordinates = [];
                var geomType = self.coordinateGeomType();
                switch (geomType) {
                    case 'Polygon':
                        rawCoordinates.push(rawCoordinates[0]);
                        coordinates = [rawCoordinates];
                        break;
                    case 'Point':
                        coordinates = rawCoordinates[0];
                        break;
                    default:
                        coordinates = rawCoordinates;
                        break;
                }
                addSelectFeatures([
                    {
                        type: 'Feature',
                        geometry: {
                            type: geomType,
                            coordinates: coordinates,
                        },
                    },
                ]);
            }
        }
    });
    self.showCoordinateFeature = function () {
        var selectedFeatureIds = self.selectedFeatureIds();
        var featureId = selectedFeatureIds[0];
        if (featureId) {
            var feature = self.draw.get(featureId);
            self.fitFeatures([feature]);
        }
    };

    self.coordinateEditing = ko.observable(false);
    self.newX = ko.observable();
    self.newY = ko.observable();
    var newCoordinatePair = ko.computed(function () {
        var x = self.newX();
        var y = self.newY();
        return [x, y];
    });
    self.focusLatestY = ko.observable(true);
    var getNewCoordinatePair = function (coords) {
        var newCoords = [ko.observable(coords[0]), ko.observable(coords[1])];
        newCoords.forEach(function (value) {
            value.subscribe(function (newValue) {
                if ([undefined, null, ''].includes(newValue)) value(0);
            });
        });
        return newCoords;
    };
    newCoordinatePair.subscribe(function (coords) {
        if (coords[0] && coords[1]) {
            self.coordinates.push(getNewCoordinatePair(coords));
            self.newX(undefined);
            self.newY(undefined);
            self.focusLatestY(true);
        }
    });
    var updateCoordinatesFromFeature = function (feature) {
        var sourceCoordinates = [];
        if (feature.geometry.type === 'Polygon') {
            sourceCoordinates = [];
            for (
                var i = 0;
                i < feature.geometry.coordinates[0].length - 1;
                i++
            ) {
                sourceCoordinates.push(feature.geometry.coordinates[0][i]);
            }
        } else if (feature.geometry.type === 'Point')
            sourceCoordinates = [feature.geometry.coordinates];
        else sourceCoordinates = feature.geometry.coordinates;
        self.coordinateGeomType(feature.geometry.type);
        self.coordinates(
            sourceCoordinates.map(function (coords) {
                var newCoords = getNewCoordinatePair(coords);
                transformCoordinatePair(newCoords, geographic);
                return newCoords;
            }),
        );
    };
    var transformCoordinatePair = function (coords, sourceCRS) {
        var targetCRS = self.selectedCoordinateReference();
        var transformedCoordinates = proj4(sourceCRS, targetCRS, [
            Number(coords[0]()),
            Number(coords[1]()),
        ]);
        coords[0](transformedCoordinates[0]);
        coords[1](transformedCoordinates[1]);
    };
    var previousCRS = self.selectedCoordinateReference();
    var transformCoordinates = function () {
        var targetCRS = self.selectedCoordinateReference();
        self.coordinates().forEach(function (coords) {
            transformCoordinatePair(coords, previousCRS);
        });
        previousCRS = targetCRS;
    };
    self.selectedCoordinateReference.subscribe(transformCoordinates);

    self.coordinateGeomType = ko.observable();
    self.coordinateEditing.subscribe(function (editing) {
        self.coordinateGeomType(null);
        var selectedTool = self.selectedTool();
        switch (selectedTool) {
            case 'draw_point':
                self.coordinateGeomType('Point');
                break;
            case 'draw_line_string':
                self.coordinateGeomType('LineString');
                break;
            case 'draw_polygon':
                self.coordinateGeomType('Polygon');
                break;
            default:
                break;
        }
        var selectedFeatureIds = self.selectedFeatureIds();
        var featureId = selectedFeatureIds[0];
        self.focusLatestY(false);
        self.coordinates([]);
        self.newX(undefined);
        self.newY(undefined);
        if (editing) {
            var selectConfig;
            if (selectedFeatureIds.length > 0) {
                selectConfig = {
                    featureIds: [featureId],
                };
                self.selectedFeatureIds([featureId]);
                var feature = self.draw.get(featureId);
                updateCoordinatesFromFeature(feature);
            }
            if (selectedTool) {
                self.draw.trash();
            }
            self.draw.changeMode('simple_select', selectConfig);
            _.each(self.featureLookup, function (value) {
                value.selectedTool(null);
            });
        }
    });
    self.hideNewCoordinates = ko.computed(function () {
        var geomType = self.coordinateGeomType();
        var coordCount = self.coordinates().length;
        return geomType === 'Point' && coordCount > 0;
    });

    self.minCoordinates = ko.computed(function () {
        var geomType = self.coordinateGeomType();
        var minCoordinates;
        switch (geomType) {
            case 'Point':
                minCoordinates = 1;
                break;
            case 'LineString':
                minCoordinates = 2;
                break;
            case 'Polygon':
                minCoordinates = 3;
                break;
            default:
                break;
        }
        return minCoordinates;
    });

    self.allowDeleteCoordinates = ko.computed(function () {
        return self.coordinates().length > self.minCoordinates();
    });

    self.editCoordinates = function () {
        self.coordinateEditing(true);
    };

    self.canEditCoordinates = ko.computed(function () {
        var featureId = self.selectedFeatureIds()[0];
        if (featureId) {
            var feature = self.draw.get(featureId);
            return ['Point', 'LineString', 'Polygon'].includes(
                feature.geometry.type,
            );
        } else {
            var selectedTool = self.selectedTool();
            return ['draw_point', 'draw_line_string', 'draw_polygon'].includes(
                selectedTool,
            );
        }
    });

    self.selectedFeatureIds.subscribe(function (ids) {
        if (ids.length === 0) self.coordinateEditing(false);
        else if (self.canEditCoordinates()) {
            var feature = self.draw.get(ids[0]);
            updateCoordinatesFromFeature(feature);
        }
    });

    self.bufferFeature = ko.computed(function () {
        return self.selectedFeatureIds()[0];
    });
    var getBufferFeature = function () {
        var featureId = self.bufferFeature();
        if (featureId) {
            return self.draw.get(featureId);
        }
    };
    self.bufferParams = ko.computed(function () {
        var bufferFeature = getBufferFeature();
        if (bufferFeature && self.bufferNodeId())
            return {
                geometry: bufferFeature.geometry,
                buffer: {
                    width: parseFloat(self.bufferDistance()),
                    unit: self.bufferUnits(),
                },
            };
    });

    self.bufferFeature.subscribe(function (bufferFeature) {
        if (!bufferFeature) self.bufferNodeId(false);
    });
    self.updateBufferFeature = function () {
        var bufferParams = self.bufferParams();
        var bufferFeature = getBufferFeature();
        if (bufferParams && bufferFeature) {
            bufferParams.geometry = bufferFeature.geometry;
            window
                .fetch(
                    arches.urls.buffer +
                        '?filter=' +
                        JSON.stringify(bufferParams),
                )
                .then(function (response) {
                    if (response.ok) {
                        return response.json();
                    }
                })
                .then(function (json) {
                    var bufferFeature = getBufferFeature();
                    self.bufferResult({
                        type: 'Feature',
                        id: uuid.generate(),
                        geometry: json,
                        properties: {
                            nodeId: bufferFeature.properties.nodeId,
                        },
                    });
                });
        } else self.bufferResult(undefined);
    };
    self.bufferParams.subscribe(self.updateBufferFeature);

    if (self.card) {
        self.card.map = self.map;
    }

    self.addBufferResult = function () {
        var bufferResult = self.bufferResult();
        if (self.bufferAddNew()) {
            var dirty = ko.unwrap(self.tile.dirty);
            var nodeId = self.bufferNodeId();
            var addBufferResultAsNew = function () {
                var updateNewTile = self.card.selected.subscribe(function () {
                    var fc = {
                        type: 'FeatureCollection',
                        features: [bufferResult],
                    };
                    self.card.getNewTile().data[nodeId](fc);
                    self.card.map.subscribe(function (map) {
                        map.fitBounds(geojsonExtent(fc), {
                            duration: 0,
                            padding: padding,
                        });
                    });
                    updateNewTile.dispose();
                });
                self.card.selected(true);
            };
            if (dirty) self.saveTile(addBufferResultAsNew);
            else addBufferResultAsNew();
        } else {
            self.draw.add(bufferResult);
            self.bufferNodeId(false);
            self.updateTiles();
            self.editFeature(bufferResult);
            self.fitFeatures([bufferResult]);
        }
    };
};
export default MapEditorViewModel;
