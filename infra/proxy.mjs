// HTTPS front door only. The application, Qwen integration and data live on AWS.
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.hostname !== 'resume.usamaaslam.site') return new Response('Not found', {status: 404});
    if (url.protocol !== 'https:') return Response.redirect(`https://${url.host}${url.pathname}${url.search}`, 301);
    const isApi = url.pathname.startsWith('/api/');
    if (!['GET', 'HEAD', 'POST'].includes(request.method)) return new Response('Method not allowed', {status: 405});
    const staticPaths = new Set(['/', '/index.html', '/studio.js', '/studio.css', '/resume.md', '/academic.md', '/general.md', '/Usama%20DP.jpeg', '/Usama%20DP%20headshot.jpeg', '/robots.txt', '/sitemap.xml']);
    if (!isApi && !staticPaths.has(url.pathname)) return new Response('Not found', {status: 404});
    const cacheKey = new Request(`${url.origin}${url.pathname}?release=${env.ASSET_VERSION || 'initial'}`, {method: 'GET'});
    if (!isApi && request.method === 'GET') {
      const cached = await caches.default.match(cacheKey);
      if (cached) return cached;
    }
    if (Number(request.headers.get('content-length') || 0) > 40000) return new Response('Request too large', {status: 413});
    const upstream = new URL(env.AWS_ORIGIN);
    upstream.pathname = url.pathname;
    upstream.search = url.search;
    const headers = new Headers(request.headers);
    headers.delete('host');
    headers.delete('authorization');
    headers.set('x-resume-origin', env.AWS_ORIGIN_SECRET);
    headers.set('x-resume-client-ip', request.headers.get('cf-connecting-ip') || 'unknown');
    try {
      const origin = await fetch(upstream, {method: request.method, headers,
        body: request.method === 'POST' ? request.body : undefined, redirect: 'manual'});
      const result = new Response(origin.body, origin);
      result.headers.set('x-content-type-options', 'nosniff');
      result.headers.set('x-frame-options', 'DENY');
      result.headers.set('strict-transport-security', 'max-age=31536000');
      result.headers.set('referrer-policy', 'same-origin');
      if (isApi) result.headers.set('cache-control', 'no-store');
      else if (origin.ok && request.method === 'GET') ctx.waitUntil(caches.default.put(cacheKey, result.clone()));
      return result;
    } catch {
      return Response.json({error: 'The AWS service is temporarily unavailable. Your draft is unchanged.'}, {status: 503, headers: {'cache-control': 'no-store'}});
    }
  }
};
