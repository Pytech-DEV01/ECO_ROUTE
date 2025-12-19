let map;
let normalLayer;
let greenLayer;
let labelLayer;
let userMarker;
let userCircle;
let redRoute;
let greenRoute;
let zoneLayers=[];
let ecoRouteData=null;
let mapNormal;
let mapGreen;
let splitMode=false;
let syncing=false;
let sseMarkers=[];
let wxEs=null;
let navMarker=null;
let navTimer=null;
let navIndex=0;
let navRoute=null;
let routesNormal=[];
let routesGreen=[];
// removed map expand/minimize toggle

async function init(){
  const prof=await fetch('/api/profile').then(r=>r.json());
  if(prof && prof.name){document.getElementById('userName').textContent=prof.name}
  // Defer map creation until Find Route is clicked
  const form=document.getElementById('routeForm');
  form.addEventListener('submit',handleFindRoute);
  document.getElementById('logoutBtn').addEventListener('click',async()=>{await fetch('/api/logout',{method:'POST'});window.location.href='/welcome'});
  startSSE();
  startWeather(12.305,76.655);
}

async function handleFindRoute(e){
  e.preventDefault();
  const from=document.getElementById('fromInput').value.trim();
  const to=document.getElementById('toInput').value.trim();
  const g1=await fetch('/api/geocode?q='+encodeURIComponent(from)).then(r=>r.json());
  const g2=await fetch('/api/geocode?q='+encodeURIComponent(to)).then(r=>r.json());
  if(g1.error||g2.error){alert('Unable to geocode');return}
  const url=`/api/route?from_lon=${g1.lon}&from_lat=${g1.lat}&to_lon=${g2.lon}&to_lat=${g2.lat}`;
  const data=await fetch(url).then(r=>r.json());
  if(data.error){alert('Routing failed');return}
  ecoRouteData=data;
  stopNavigation();
  clearRoutesBoth();
  enableSplitMaps();
  drawZonesBoth(data.zones);
  drawRoutesBoth(data.polluted,data.eco);
  updateMetrics(data.eco);
  showDirections(data);
  try{ if(wxEs){wxEs.close()} }catch{}
  const toLat=g2.lat, toLon=g2.lon;
  startWeather(toLat,toLon);
  const startBtn=document.getElementById('startNav');
  const stopBtn=document.getElementById('stopNav');
  if(startBtn){ startBtn.onclick=()=>{ startNavigation(data.eco) } }
  if(stopBtn){ stopBtn.onclick=stopNavigation }
}

function drawZones(zones){
  zoneLayers.forEach(z=>map.removeLayer(z));
  zoneLayers=[];
  zones.forEach(z=>{
    const c=L.circle([z.lat,z.lon],{radius:z.radius_m,weight:1,color:'#1b4332',fillColor:'#2d6a4f',fillOpacity:0.15});
    c.addTo(map);
    zoneLayers.push(c);
  })
}

function drawZonesOn(targetMap,zones){
  zones.forEach(z=>{
    const c=L.circle([z.lat,z.lon],{radius:z.radius_m,weight:1,color:'#1b4332',fillColor:'#2d6a4f',fillOpacity:0.15});
    c.addTo(targetMap);
    zoneLayers.push(c);
  })
}
function drawZonesBoth(zones){
  clearZoneLayers();
  drawZonesOn(mapNormal,zones);
  drawZonesOn(mapGreen,zones);
}
function clearZoneLayers(){
  zoneLayers.forEach(l=>{try{map.removeLayer(l)}catch{} try{mapNormal.removeLayer(l)}catch{} try{mapGreen.removeLayer(l)}catch{}});
  zoneLayers=[];
}

function drawRoutes(shortest,eco){
  if(redRoute){map.removeLayer(redRoute)}
  if(greenRoute){map.removeLayer(greenRoute)}
  redRoute=L.polyline(shortest.geometry.map(([lon,lat])=>[lat,lon]),{color:'#e63946',weight:5}).addTo(map);
  greenRoute=L.polyline(eco.geometry.map(([lon,lat])=>[lat,lon]),{color:'#2a9d8f',weight:5}).addTo(map);
  const group=L.featureGroup([redRoute,greenRoute]);
  map.fitBounds(group.getBounds(),{padding:[20,20]});
}

function drawRoutesOn(targetMap,shortest,eco){
  const r1=L.polyline(shortest.geometry.map(([lon,lat])=>[lat,lon]),{color:'#e63946',weight:5}).addTo(targetMap);
  const r2=L.polyline(eco.geometry.map(([lon,lat])=>[lat,lon]),{color:'#2a9d8f',weight:5}).addTo(targetMap);
  const group=L.featureGroup([r1,r2]);
  targetMap.fitBounds(group.getBounds(),{padding:[20,20]});
  if(targetMap===mapNormal){routesNormal.push(r1,r2)} else if(targetMap===mapGreen){routesGreen.push(r1,r2)}
}
function drawRoutesBoth(shortest,eco){
  clearRoutesBoth();
  drawRoutesOn(mapNormal,shortest,eco);
  drawRoutesOn(mapGreen,shortest,eco);
}
function clearRoutesBoth(){
  try{routesNormal.forEach(r=>mapNormal.removeLayer(r))}catch{}
  try{routesGreen.forEach(r=>mapGreen.removeLayer(r))}catch{}
  routesNormal=[]; routesGreen=[];
}

function updateMetrics(rt){
  setText('ecoScore',rt.eco_score);
  setText('aqi',rt.avg_aqi);
  setText('co2',rt.co2_kg);
  const rate=(rt.co2_kg/(rt.duration_min/60)).toFixed(3)+' kg/h';
  setText('co2Rate',rate);
}

function setText(id,val){
  document.getElementById(id).textContent=val
}

function startSSE(){
  const es=new EventSource('/api/aqi-stream');
  es.onmessage=e=>{
    try{
      const payload=JSON.parse(e.data);
      if(!payload||!Array.isArray(payload))return;
      if(!splitMode || !mapNormal || !mapGreen) return;
      let worst=null;
      sseMarkers.forEach(m=>{try{mapNormal.removeLayer(m)}catch{} try{mapGreen.removeLayer(m)}catch{}});
      sseMarkers=[];
      payload.forEach(p=>{
        const style={radius:6,color:aqiColor(p.aqi),fillColor:aqiColor(p.aqi),fillOpacity:0.9};
        const r1=L.circleMarker([p.lat,p.lon],style).addTo(mapNormal);
        const r2=L.circleMarker([p.lat,p.lon],style).addTo(mapGreen);
        r1.bindTooltip(`${p.name}: Eco ${p.eco_score}`,{permanent:true,direction:'top',className:'eco-tip'});
        r2.bindTooltip(`${p.name}: Eco ${p.eco_score}`,{permanent:true,direction:'top',className:'eco-tip'});
        r1.on('click',()=>L.popup().setLatLng([p.lat,p.lon]).setContent(`${p.name}<br>AQI: ${p.aqi}<br>Eco: ${p.eco_score}<br>CO₂ rate: ${p.co2_rate_kgh} kg/h`).openOn(mapNormal));
        r2.on('click',()=>L.popup().setLatLng([p.lat,p.lon]).setContent(`${p.name}<br>AQI: ${p.aqi}<br>Eco: ${p.eco_score}<br>CO₂ rate: ${p.co2_rate_kgh} kg/h`).openOn(mapGreen));
        sseMarkers.push(r1);sseMarkers.push(r2);
        if(!worst||p.aqi>worst.aqi)worst=p;
      });
      if(worst){
        const popup=L.popup({autoClose:true}).setLatLng([worst.lat,worst.lon]).setContent('High AQI: '+worst.name+' • '+worst.aqi);
        popup.openOn(mapNormal)
      }
      if(ecoRouteData&&ecoRouteData.eco){
        const rt=ecoRouteData.eco;
        const avg=payload.reduce((a,b)=>a+b.aqi,0)/payload.length;
        const adj=Math.max(0,100-(avg*0.6));
        setText('aqi',avg.toFixed(1));
        setText('ecoScore',adj.toFixed(1));
      }
    }catch{}
  }
}

function aqiColor(a){
  if(a<=50)return '#2d6a4f';
  if(a<=100)return '#b7e4c7';
  if(a<=150)return '#ffd166';
  if(a<=200)return '#f4a261';
  if(a<=300)return '#e76f51';
  return '#9d0208';
}

function enableGreenery(){
  if(map.hasLayer(normalLayer)) map.removeLayer(normalLayer);
  if(!map.hasLayer(greenLayer)) greenLayer.addTo(map);
  if(!map.hasLayer(labelLayer)) labelLayer.addTo(map);
  map.invalidateSize();
  const mysoreBounds=L.latLngBounds([[12.26,76.57],[12.38,76.71]]);
  if(navigator.geolocation){
    navigator.geolocation.getCurrentPosition(pos=>{
      const lat=pos.coords.latitude;const lon=pos.coords.longitude;const acc=pos.coords.accuracy||100;
      if(userMarker){map.removeLayer(userMarker)}
      if(userCircle){map.removeLayer(userCircle)}
      userMarker=L.marker([lat,lon]).addTo(map).bindPopup('You are here').openPopup();
      userCircle=L.circle([lat,lon],{radius:acc, color:'#2a9d8f', fillColor:'#2a9d8f', fillOpacity:0.2}).addTo(map);
      map.setView([lat,lon],14);
    },()=>{
      map.fitBounds(mysoreBounds,{padding:[20,20]});
    },{enableHighAccuracy:true,timeout:4000,maximumAge:60000});
  }else{
    map.fitBounds(mysoreBounds,{padding:[20,20]});
  }
}

function enableSplitMaps(){
  const single=document.getElementById('map');
  const split=document.getElementById('mapSplit');
  const toggle=document.querySelector('.layer-toggle');
  const wrap=document.querySelector('.map-wrap');
  wrap.classList.remove('hidden');
  split.classList.remove('hidden');
  single.classList.add('hidden');
  // map displayed at bottom, no toggle
  if(toggle) toggle.style.display='none';
  if(!mapNormal){
    mapNormal=L.map('mapNormal').setView([12.305,76.655],12);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap',maxZoom:19}).addTo(mapNormal);
  }
  if(!mapGreen){
    mapGreen=L.map('mapGreen').setView([12.305,76.655],12);
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{attribution:'Tiles © Esri WorldImagery',maxZoom:19}).addTo(mapGreen);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}.png',{attribution:'© CARTO labels',maxZoom:19}).addTo(mapGreen);
  }
  mapNormal.on('move',()=>{if(syncing)return; syncing=true; const c=mapNormal.getCenter(); const z=mapNormal.getZoom(); mapGreen.setView(c,z,{animate:false}); syncing=false});
  mapGreen.on('move',()=>{if(syncing)return; syncing=true; const c=mapGreen.getCenter(); const z=mapGreen.getZoom(); mapNormal.setView(c,z,{animate:false}); syncing=false});
  splitMode=true;
  // removed click-to-toggle behavior
  // back button removed
}

function transportIcon(){
  const mode=(document.getElementById('modeSelect')?.value)||'car';
  const html= mode==='car' ? '🚗' : '🛵';
  return L.divIcon({html:`<span class="nav-emoji">${html}</span>`,className:'',iconSize:[24,24],iconAnchor:[12,12]});
}

function startNavigation(route){
  stopNavigation();
  navRoute=route.geometry.map(([lon,lat])=>[lat,lon]);
  navIndex=0;
  const start=navRoute[0];
  if(!start) return;
  if(navMarker){try{mapNormal.removeLayer(navMarker)}catch{}}
  navMarker=L.marker(start,{icon:transportIcon()}).addTo(mapNormal);
  document.getElementById('mapSplit')?.classList.add('tilt');
  const mode=(document.getElementById('modeSelect')?.value)||'car';
  const speed= mode==='car' ? 45 : 25; // km/h
  const stepMs=200;
  const stepDistKm= speed*(stepMs/3600000);
  navTimer=setInterval(()=>{
    if(!navRoute||navIndex>=navRoute.length-1){stopNavigation();return}
    const cur=navRoute[navIndex];
    const nxt=navRoute[navIndex+1];
    const d=haversine(cur[0],cur[1],nxt[0],nxt[1]);
    if(d<=stepDistKm){navIndex++;navMarker.setLatLng(nxt)} else {
      const t=stepDistKm/d;
      const lat=cur[0]+(nxt[0]-cur[0])*t;
      const lon=cur[1]+(nxt[1]-cur[1])*t;
      navMarker.setLatLng([lat,lon]);
    }
    mapNormal.setView(navMarker.getLatLng(), mapNormal.getZoom(), {animate:false});
  }, stepMs);
}

function stopNavigation(){
  try{ if(navTimer){clearInterval(navTimer);navTimer=null} }catch{}
  try{ document.getElementById('mapSplit')?.classList.remove('tilt') }catch{}
}

function haversine(lat1, lon1, lat2, lon2){
  const R=6371;
  const toRad=x=>x*Math.PI/180;
  const dLat=toRad(lat2-lat1);
  const dLon=toRad(lon2-lon1);
  const a=Math.sin(dLat/2)**2 + Math.cos(toRad(lat1))*Math.cos(toRad(lat2))*Math.sin(dLon/2)**2;
  const c=2*Math.atan2(Math.sqrt(a),Math.sqrt(1-a));
  return R*c;
}


function startWeather(lat,lon){
  try{ if(wxEs){wxEs.close()} }catch{}
  wxEs=new EventSource(`/api/weather-stream?lat=${lat}&lon=${lon}`);
  wxEs.onmessage=e=>{
    try{
      const w=JSON.parse(e.data);
      if(!w) return;
      setText('wxTemp', (w.temperature_c!=null? w.temperature_c.toFixed(1)+' °C':'–'));
      setText('wxHumidity', (w.humidity!=null? w.humidity+' %':'–'));
    }catch{}
  }
}

function showDirections(data){
  const box=document.getElementById('directions');
  const list=document.getElementById('dirList');
  box.classList.remove('hidden');
  const polluted=data.polluted; const eco=data.eco;
  function render(route){
    list.innerHTML='';
    route.steps.forEach((s,i)=>{
      const el=document.createElement('div');
      el.className='dir-step';
      el.innerHTML=`<div>${i+1}. ${s.text}</div><div class='sm'>${(s.distance_m/1000).toFixed(2)} km • ${(s.duration_s/60).toFixed(1)} min</div>`;
      el.addEventListener('click',()=>{
        const loc=s.location; if(!loc||loc.length<2)return; const lat=loc[1], lon=loc[0];
        mapNormal.setView([lat,lon],15); mapGreen.setView([lat,lon],15);
      });
      list.appendChild(el);
    })
  }
  document.getElementById('tabPolluted').onclick=()=>render(polluted);
  document.getElementById('tabEco').onclick=()=>render(eco);
  render(eco);
}

window.addEventListener('DOMContentLoaded',init);
