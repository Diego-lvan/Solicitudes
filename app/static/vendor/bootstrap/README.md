# Bootstrap 5 vendor assets

The CSS/JS files in this directory are placeholders. Replace them with the
official Bootstrap 5 minified bundles before shipping. Recommended:

```
curl -L -o bootstrap.min.css https://cdn.jsdelivr.net/npm/bootstrap@5.3/dist/css/bootstrap.min.css
curl -L -o bootstrap.bundle.min.js https://cdn.jsdelivr.net/npm/bootstrap@5.3/dist/js/bootstrap.bundle.min.js
```

(We vendor instead of using a CDN per RT-04 and to stay offline-friendly.)
