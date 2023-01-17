define([
    'jquery',
    'knockout',
    'underscore',
    'dropzone',
    'uuid',
    'viewmodels/widget',
    'bindings/gallery',
    'bindings/dropzone',
    'templates/views/components/widgets/photo.htm'
], function($, ko, _, Dropzone, uuid, WidgetViewModel, GalleryBinding, DropzoneBinding, defaultPhotoTemplate) {
    /**
     * registers a file-widget component for use in forms
     * @function external:"ko.components".file-widget
     * @param {object} params
     * @param {string} params.value - the value being managed
     * @param {function} params.config - observable containing config object
     * @param {string} params.config().acceptedFiles - accept attribute value for file input
     * @param {string} params.config().maxFilesize - maximum allowed file size in MB
     */

    return ko.components.register('photo-widget', {
        viewModel: function(params) {
            params.configKeys = ['acceptedFiles', 'maxFilesize'];
            var self = this;
            WidgetViewModel.apply(this, [params]);

            this.uploadedFiles = ko.observableArray();
            this.unsupportedImageTypes = ['tif', 'tiff', 'vnd.adobe.photoshop'];

            if (Array.isArray(self.value())) {
                this.uploadedFiles(self.value());
            }

            this.hoveredOverImage = ko.observable(false);

            this.toggleHoveredOverImage = function(val, event){
                var res = event.target === event.toElement ? true : false;
                this.hoveredOverImage(res);
            };

            this.reportImages = ko.computed(function() {
                // return [];
                return self.uploadedFiles().filter(function(file) {
                    var fileType = ko.unwrap(file.type);
                    if (fileType) {
                        var ext = fileType.split('/').pop();
                        return fileType.indexOf('image') >= 0 && self.unsupportedImageTypes.indexOf(ext) <= 0;
                    }
                    return false;
                });
            });

        },
        template: defaultPhotoTemplate
    });

});