/**
 * CloudFront Function — viewer request. Directory-index rewriting.
 *
 * Why this exists
 * ---------------
 * tools/generate_static_meta.py writes per-route files as
 * `dist/read/852/index.html` so that `aws s3 sync` assigns them text/html
 * (extensionless keys would upload as binary/octet-stream and download rather
 * than render). S3 REST origins — unlike S3 *website* endpoints — do not serve
 * directory index documents, so a request for `/read/852` would 404 without
 * this function. Website endpoints would handle it natively but cannot be used
 * with Origin Access Control, which would mean making the bucket public: a
 * security regression this project deliberately refuses.
 *
 * Behaviour
 * ---------
 *   /read/852        -> /read/852/index.html
 *   /about/          -> /about/index.html
 *   /                -> untouched (DefaultRootObject already resolves it)
 *   /assets/x-a1b2.js-> untouched (has an extension)
 *   /og-image.png    -> untouched (has an extension)
 *
 * Requests that rewrite to a key with no object behind it (e.g. /scripture/*,
 * which is deliberately not pre-generated) still fall through to the existing
 * 403/404 -> /index.html rule in the distribution config, so the SPA renders
 * and nothing regresses.
 *
 * Runtime note
 * ------------
 * Written against cloudfront-js-1.0, whose runtime is ES5.1 plus only a
 * partial set of later features. `String.prototype.endsWith` / `includes` are
 * NOT safe to assume there, so this uses `indexOf` and `charAt` throughout.
 * The code is also valid under cloudfront-js-2.0 if the function is ever
 * moved to that runtime.
 *
 * Deploy: see infra/README.md. Attach to the default cache behaviour as a
 * viewer-request function. Costs roughly $0.10 per million invocations.
 */
function handler(event) {
    var request = event.request;
    var uri = request.uri;

    // Root: DefaultRootObject (index.html) already covers this.
    if (uri === '/') {
        return request;
    }

    // Trailing slash: append the index document directly.
    if (uri.charAt(uri.length - 1) === '/') {
        request.uri = uri + 'index.html';
        return request;
    }

    // Look for an extension in the LAST path segment only. Checking the whole
    // URI would wrongly skip a path such as /browse/v1.2/detail, where the dot
    // belongs to a directory rather than to a filename.
    var lastSlash = uri.lastIndexOf('/');
    var lastSegment = uri.substring(lastSlash + 1);

    if (lastSegment.indexOf('.') === -1) {
        request.uri = uri + '/index.html';
    }

    return request;
}
