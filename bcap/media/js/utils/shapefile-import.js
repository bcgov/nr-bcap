import { iter as iterateZipEntries } from 'but-unzip';

const fileParts = (file) => {
    const dot = file.name.lastIndexOf('.');
    return {
        basename:
            dot === -1
                ? file.name.toLowerCase()
                : file.name.slice(0, dot).toLowerCase(),
        extension: dot === -1 ? '' : file.name.slice(dot + 1).toLowerCase(),
    };
};

export const readFile = (file, mode) => {
    return new Promise((resolve, reject) => {
        const reader = new window.FileReader();
        const rejectRead = () =>
            reject(new Error('Unable to read file: "' + file.name + '"'));
        reader.onload = (event) => resolve(event.target.result);
        reader.onerror = rejectRead;
        reader.onabort = rejectRead;
        try {
            if (mode === 'arrayBuffer') reader.readAsArrayBuffer(file);
            else reader.readAsText(file);
        } catch (error) {
            reject(error);
        }
    });
};

export const parseKmlText = (contents, domParser, convertKml) => {
    const document = domParser.parseFromString(contents, 'text/xml');
    if (document.getElementsByTagName('parsererror').length > 0)
        throw new Error('KML document is malformed');
    return convertKml(document);
};

const assertFeatureCollections = (geoJSON) => {
    const collections = Array.isArray(geoJSON) ? geoJSON : [geoJSON];
    const isValid =
        collections.length > 0 &&
        collections.every(
            (collection) =>
                collection &&
                collection.type === 'FeatureCollection' &&
                Array.isArray(collection.features) &&
                collection.features.every(
                    (feature) => feature && feature.type === 'Feature',
                ),
        );
    if (!isValid)
        throw new Error(
            'Imported data is not a valid GeoJSON FeatureCollection',
        );
};

const coordinatesAreWGS84 = (coordinates) => {
    if (!Array.isArray(coordinates)) return true;
    if (typeof coordinates[0] === 'number') {
        return (
            Number.isFinite(coordinates[0]) &&
            Number.isFinite(coordinates[1]) &&
            Math.abs(coordinates[0]) <= 180 &&
            Math.abs(coordinates[1]) <= 90
        );
    }
    return coordinates.every(coordinatesAreWGS84);
};

// B.C. spans approximately 48-60 N and 139-114 W. This one-degree
// operational buffer accommodates coastal/border data without accepting a
// plausible projection result elsewhere in the world. It cannot detect an
// internally wrong .prj whose transformed coordinates still land in B.C.
const BUFFERED_BC_ENVELOPE = {
    minLongitude: -140,
    maxLongitude: -113,
    minLatitude: 47,
    maxLatitude: 61,
};

const coordinatesAreInBritishColumbia = (coordinates) => {
    if (!Array.isArray(coordinates)) return true;
    if (typeof coordinates[0] === 'number') {
        return (
            coordinates[0] >= BUFFERED_BC_ENVELOPE.minLongitude &&
            coordinates[0] <= BUFFERED_BC_ENVELOPE.maxLongitude &&
            coordinates[1] >= BUFFERED_BC_ENVELOPE.minLatitude &&
            coordinates[1] <= BUFFERED_BC_ENVELOPE.maxLatitude
        );
    }
    return coordinates.every(coordinatesAreInBritishColumbia);
};

const geometryCoordinatesPass = (geometry, predicate) => {
    if (!geometry) return true;
    if (geometry.type === 'GeometryCollection')
        return geometry.geometries.every((item) =>
            geometryCoordinatesPass(item, predicate),
        );
    return predicate(geometry.coordinates);
};

const geometryIsWGS84 = (geometry) =>
    geometryCoordinatesPass(geometry, coordinatesAreWGS84);

const geometryIsInBritishColumbia = (geometry) =>
    geometryCoordinatesPass(geometry, coordinatesAreInBritishColumbia);

const assertWGS84 = (geoJSON) => {
    const collections = Array.isArray(geoJSON) ? geoJSON : [geoJSON];
    const isWGS84 = collections.every((collection) =>
        collection.features.every((feature) =>
            geometryIsWGS84(feature.geometry),
        ),
    );
    if (!isWGS84)
        throw new Error('Projection did not transform coordinates to WGS84');

    const isInBritishColumbia = collections.every((collection) =>
        collection.features.every((feature) =>
            geometryIsInBritishColumbia(feature.geometry),
        ),
    );
    if (!isInBritishColumbia)
        throw new Error(
            'Shapefile coordinates fall outside the supported B.C. area',
        );
};

const inspectZipProjections = async (buffer, validateProjection) => {
    const entries = Array.from(iterateZipEntries(new Uint8Array(buffer)));
    const shapefiles = new Map();
    const projections = new Map();

    entries.forEach((entry) => {
        const parts = fileParts({ name: entry.filename });
        const destination =
            parts.extension === 'shp'
                ? shapefiles
                : parts.extension === 'prj'
                  ? projections
                  : null;
        if (destination) {
            const matches = destination.get(parts.basename) || [];
            matches.push(entry);
            destination.set(parts.basename, matches);
        }
    });

    if (shapefiles.size === 0)
        throw new Error('ZIP archive contains no shapefiles');

    for (const [basename, matchingShapefiles] of shapefiles) {
        const shapefileName = matchingShapefiles[0].filename;
        if (matchingShapefiles.length > 1)
            throw new Error(
                'Archived shapefile is ambiguous: "' + shapefileName + '"',
            );
        const matchingProjections = projections.get(basename) || [];
        if (matchingProjections.length === 0)
            throw new Error(
                'Projection file missing for archived shapefile: "' +
                    shapefileName +
                    '"',
            );
        if (matchingProjections.length > 1)
            throw new Error(
                'Projection file is ambiguous for archived shapefile: "' +
                    shapefileName +
                    '"',
            );
        const shapefileBasename = shapefileName.slice(
            0,
            shapefileName.lastIndexOf('.'),
        );
        const projectionName = matchingProjections[0].filename;
        const projectionBasename = projectionName.slice(
            0,
            projectionName.lastIndexOf('.'),
        );
        // shpjs normalizes extensions but resolves sidecars by a
        // case-sensitive path. Reject a case-only mismatch rather than
        // validating a .prj that shpjs would silently ignore.
        if (projectionBasename !== shapefileBasename)
            throw new Error(
                'Projection filename does not exactly match archived shapefile: "' +
                    shapefileName +
                    '"',
            );
        const projectionBytes = await matchingProjections[0].read();
        validateProjection(new TextDecoder().decode(projectionBytes));
    }
};

const emptyFeatureCollection = () => ({
    type: 'FeatureCollection',
    features: [],
});

export const finishDroppedFileImport = async (
    processing,
    nodeId,
    addFromGeoJSON,
    setErrors,
) => {
    try {
        const result = await processing;
        const errors = result.errors.concat(
            addFromGeoJSON(JSON.stringify(result.geoJSON), nodeId),
        );
        setErrors(errors);
        return { geoJSON: result.geoJSON, errors };
    } catch (error) {
        const errors = [
            {
                message:
                    'Unable to import dropped files: ' +
                    (error && error.message ? error.message : String(error)),
            },
        ];
        setErrors(errors);
        return { geoJSON: emptyFeatureCollection(), errors };
    }
};

export const processDroppedFiles = async (files, dependencies) => {
    const fileList = Array.from(files);
    const projections = new Map();
    const dataFiles = new Map();
    const encodingFiles = new Map();

    fileList.forEach((file) => {
        const parts = fileParts(file);
        const destination =
            parts.extension === 'prj'
                ? projections
                : parts.extension === 'dbf'
                  ? dataFiles
                  : parts.extension === 'cpg'
                    ? encodingFiles
                    : null;
        if (destination) {
            const matchingFiles = destination.get(parts.basename) || [];
            matchingFiles.push(file);
            destination.set(parts.basename, matchingFiles);
        }
    });

    const results = await Promise.all(
        fileList.map(async (file) => {
            const parts = fileParts(file);
            if (['prj', 'dbf', 'shx', 'cpg', 'qpj'].includes(parts.extension))
                return {};
            if (
                !['kml', 'json', 'geojson', 'shp', 'zip'].includes(
                    parts.extension,
                )
            ) {
                return {
                    error: {
                        message: 'File unsupported: "' + file.name + '"',
                    },
                };
            }

            if (parts.extension === 'shp') {
                const projectionFiles = projections.get(parts.basename) || [];
                if (projectionFiles.length === 0) {
                    return {
                        error: {
                            message:
                                'Projection file missing for shapefile: "' +
                                file.name +
                                '"',
                        },
                    };
                }
                if (projectionFiles.length > 1) {
                    return {
                        error: {
                            message:
                                'Projection file is ambiguous for shapefile: "' +
                                file.name +
                                '"',
                        },
                    };
                }
                const projectionFile = projectionFiles[0];
                const matchingDataFiles = dataFiles.get(parts.basename) || [];
                const matchingEncodingFiles =
                    encodingFiles.get(parts.basename) || [];
                if (
                    matchingDataFiles.length > 1 ||
                    matchingEncodingFiles.length > 1
                ) {
                    return {
                        error: {
                            message:
                                'Shapefile sidecar is ambiguous for: "' +
                                file.name +
                                '"',
                        },
                    };
                }
                try {
                    const filesToRead = [
                        dependencies.readFile(file, 'arrayBuffer'),
                        dependencies.readFile(projectionFile, 'text'),
                    ];
                    if (matchingDataFiles.length === 1)
                        filesToRead.push(
                            dependencies.readFile(
                                matchingDataFiles[0],
                                'arrayBuffer',
                            ),
                        );
                    if (matchingEncodingFiles.length === 1)
                        filesToRead.push(
                            dependencies.readFile(
                                matchingEncodingFiles[0],
                                'text',
                            ),
                        );
                    const fileContents = await Promise.all(filesToRead);
                    const shapefileBuffer = fileContents[0];
                    const projection = fileContents[1];
                    dependencies.validateProjection(projection);
                    const shapefileParts = {
                        shp: shapefileBuffer,
                        prj: projection,
                    };
                    let nextContent = 2;
                    if (matchingDataFiles.length === 1) {
                        shapefileParts.dbf = fileContents[nextContent];
                        nextContent += 1;
                    }
                    if (matchingEncodingFiles.length === 1)
                        shapefileParts.cpg = fileContents[nextContent];
                    // shpjs does not consume .shx when parsing an in-memory
                    // object, so that optional index sidecar is intentionally
                    // ignored.
                    const geoJSON =
                        await dependencies.parseShapefile(shapefileParts);
                    assertFeatureCollections(geoJSON);
                    assertWGS84(geoJSON);
                    return { geoJSON };
                } catch (error) {
                    return {
                        error: {
                            message:
                                'Unable to import shapefile "' +
                                file.name +
                                '": ' +
                                error.message,
                        },
                    };
                }
            }

            try {
                if (parts.extension === 'zip') {
                    const buffer = await dependencies.readFile(
                        file,
                        'arrayBuffer',
                    );
                    await inspectZipProjections(
                        buffer,
                        dependencies.validateProjection,
                    );
                    const geoJSON = await dependencies.parseShapefile(buffer);
                    assertFeatureCollections(geoJSON);
                    assertWGS84(geoJSON);
                    return { geoJSON };
                }
                const contents = await dependencies.readFile(file, 'text');
                const geoJSON =
                    parts.extension === 'kml'
                        ? dependencies.parseKml(contents)
                        : JSON.parse(contents);
                assertFeatureCollections(geoJSON);
                return { geoJSON };
            } catch (error) {
                return {
                    error: {
                        message:
                            'Unable to import file "' +
                            file.name +
                            '": ' +
                            error.message,
                    },
                };
            }
        }),
    );

    return {
        geoJSON: {
            type: 'FeatureCollection',
            features: results.reduce((features, result) => {
                const collections = Array.isArray(result.geoJSON)
                    ? result.geoJSON
                    : [result.geoJSON];
                collections.forEach((collection) => {
                    if (collection && collection.features)
                        features.push(...collection.features);
                });
                return features;
            }, []),
        },
        errors: results.reduce((errors, result) => {
            if (result.error) errors.push(result.error);
            return errors;
        }, []),
    };
};
