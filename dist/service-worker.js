// Public application shell only. Authenticated API responses never enter CacheStorage.
const CACHE='xuanhoa-shell-6afb4eae73787a691f38';
const FILES=['/','/app.js','/styles.css','/assets/logo-xuan-hoa.png'];
self.addEventListener('install',event=>{
  event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(FILES)).then(()=>self.skipWaiting()));
});
self.addEventListener('activate',event=>{
  event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key.startsWith('xuanhoa-shell-')&&key!==CACHE).map(key=>caches.delete(key)))).then(()=>self.clients.claim()));
});
self.addEventListener('fetch',event=>{
  const url=new URL(event.request.url);
  if(event.request.method!=='GET'||url.origin!==self.location.origin||url.pathname.startsWith('/api/'))return;
  const navigation=event.request.mode==='navigate';
  if(!navigation&&!FILES.includes(url.pathname))return;
  event.respondWith((async()=>{
    const cache=await caches.open(CACHE),key=navigation?'/':url.pathname;
    // Avoid a network attempt when the browser already reports no connection.
    if(!self.navigator.onLine){const cached=await cache.match(key);if(cached)return cached;}
    try{
      const response=await fetch(event.request);
      if(response.ok)await cache.put(key,response.clone());
      if(response.ok||!navigation)return response;
    }catch{}
    const cached=await cache.match(key);
    return cached||new Response('Chưa có bản dùng khi mất mạng. Mở ứng dụng khi có kết nối trước.',{status:503,headers:{'Content-Type':'text/plain; charset=utf-8'}});
  })());
});
