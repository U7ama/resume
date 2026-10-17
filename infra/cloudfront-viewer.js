function handler(event) {
  var request = event.request;
  var api = request.uri.indexOf('/api/') === 0;
  var paths = ['/', '/index.html', '/studio.js', '/studio.css', '/resume.md', '/academic.md', '/general.md',
    '/Usama%20DP.jpeg', '/Usama%20DP%20headshot.jpeg', '/robots.txt', '/sitemap.xml'];
  function reject(code, description) {
    return {statusCode: code, statusDescription: description, headers: {'cache-control': {value: 'no-store'}}};
  }
  if (['GET', 'HEAD', 'POST'].indexOf(request.method) < 0) return reject(405, 'Method Not Allowed');
  if (!api && paths.indexOf(request.uri) < 0) return reject(404, 'Not Found');
  if (Number((request.headers['content-length'] || {}).value || 0) > 40000) return reject(413, 'Content Too Large');
  request.headers['x-resume-client-ip'] = {value: event.viewer.ip};
  delete request.headers['x-resume-origin'];
  return request;
}
