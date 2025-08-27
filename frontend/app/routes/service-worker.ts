// Empty service worker to prevent 404 errors when browsers request it
export function loader() {
  const serviceWorkerScript = `
// Empty service worker
self.addEventListener('install', function(event) {
  self.skipWaiting();
});

self.addEventListener('activate', function(event) {
  event.waitUntil(clients.claim());
});
`;

  return new Response(serviceWorkerScript, {
    headers: {
      'Content-Type': 'application/javascript',
      'Cache-Control': 'no-cache, no-store, must-revalidate',
    },
  });
}