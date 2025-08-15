## Developing the Vue UI using Vite
### 1. Vite integration
Vite has been integrated alongside Webpack to allow more streamlined UI development. Only sections targeted to be hosted
by Vite have been modified. Currently bundling for deployment is still done using webpack.

Changes made to support development in Vite are:
1. Overriding the Arches core `templates/base-root.htm` to inject the Vite tags
2. Adding the django-vite plugin and adding configuration in settings.py
3. Adding a `context_processors.py` to toggle between 100% webpack and Vite for targeted sections

### 2. To use the Vite server
1. In `settings.py` edit the following line:
```python
USE_VITE = False # <- Change this to True to use Vite
```
1. Rebuild w/ webpack: `npm run build_development`
2. Run the Vite dev server: `npm run vite_dev`

The `settings.py` USE_VITE flag can be toggled back and forth without having to rebuild with Webpack. Just perform a
hard refresh in your browser.

### 3. Adding a new Vite-served component

