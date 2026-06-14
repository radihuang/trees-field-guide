let allPhotos = [];
let currentPhoto = null;
let leafletMap = null;
let showingAll = false;

async function init() {
  const res = await fetch('trees.json');
  const data = await res.json();
  allPhotos = data.photos.filter(p => p.filename).reverse();

  const featured = allPhotos.filter(p => p.featured);
  renderGallery(featured);

  const btn = document.getElementById('toggleAll');
  btn.textContent = `View all specimens (${allPhotos.length})`;
  btn.addEventListener('click', () => {
    showingAll = !showingAll;
    renderGallery(showingAll ? allPhotos : featured);
    btn.textContent = showingAll
      ? 'Show featured only'
      : `View all specimens (${allPhotos.length})`;
  });
}

// ── Gallery ───────────────────────────────────────────────────────────────────

function renderGallery(photos) {
  const gallery = document.getElementById('gallery');
  gallery.innerHTML = photos.map(p => `
    <div class="card" data-id="${p.id}">
      <img src="photos/${p.filename}" alt="${p.species_common_en || p.id}" loading="lazy">
      <div class="card-overlay">
        <span class="o-common">${p.species_common_en || '—'}</span>
        <span class="o-sci">${p.species_scientific || ''}</span>
      </div>
    </div>
  `).join('');

  gallery.querySelectorAll('.card').forEach(card => {
    card.addEventListener('click', () => {
      const photo = allPhotos.find(p => p.id === card.dataset.id);
      if (photo) openModal(photo);
    });
  });
}

// ── Modal ─────────────────────────────────────────────────────────────────────

function openModal(photo) {
  currentPhoto = photo;
  document.getElementById('modal').classList.remove('hidden');
  document.body.style.overflow = 'hidden';

  document.getElementById('modalPhoto').src = `photos/${photo.filename}`;
  document.getElementById('modalCommon').textContent =
    photo.species_common_en || photo.species_scientific || 'Unknown species';
  document.getElementById('modalScientific').textContent =
    photo.species_scientific || '';
  document.getElementById('modalZh').textContent =
    photo.species_common_zh || '';
  document.getElementById('modalLocation').textContent =
    photo.location_en || '—';
  document.getElementById('modalDate').textContent =
    photo.date || '—';
  document.getElementById('modalCoords').textContent =
    photo.lat != null
      ? `${photo.lat.toFixed(4)}°, ${photo.lng.toFixed(4)}°`
      : '—';
  document.getElementById('modalNote').textContent =
    photo.personal_note || '';

  switchTab('graph');
  renderGraph(photo);
}

function closeModal() {
  document.getElementById('modal').classList.add('hidden');
  document.body.style.overflow = '';
  if (leafletMap) { leafletMap.remove(); leafletMap = null; }
  document.getElementById('graphView').innerHTML = '';
}

function switchTab(tab) {
  document.getElementById('tabGraph').classList.toggle('active', tab === 'graph');
  document.getElementById('tabMap').classList.toggle('active', tab === 'map');
  document.getElementById('graphView').classList.toggle('hidden', tab !== 'graph');
  document.getElementById('mapView').classList.toggle('hidden', tab !== 'map');
}

// ── D3 Force Graph ────────────────────────────────────────────────────────────

function relatedPhotos(photo) {
  return allPhotos.filter(p =>
    p.id !== photo.id && (
      (p.species_scientific && p.species_scientific === photo.species_scientific) ||
      (p.location_en && p.location_en === photo.location_en)
    )
  );
}

function renderGraph(photo) {
  const container = document.getElementById('graphView');
  container.innerHTML = '';

  const related = relatedPhotos(photo);

  if (related.length === 0) {
    container.innerHTML = '<div class="no-related">No related photos found</div>';
    return;
  }

  const W = container.offsetWidth  || 800;
  const H = container.offsetHeight || 300;

  const nodes = [photo, ...related].map(p => ({
    id:        p.id,
    label:     p.species_common_en || p.species_scientific || '?',
    isCurrent: p.id === photo.id,
    data:      p,
  }));

  const links = related.map(p => ({
    source: photo.id,
    target: p.id,
    kind:   p.species_scientific === photo.species_scientific ? 'species' : 'location',
  }));

  const svg = d3.select(container).append('svg')
    .attr('width', W).attr('height', H);

  const sim = d3.forceSimulation(nodes)
    .force('link',      d3.forceLink(links).id(d => d.id).distance(90))
    .force('charge',    d3.forceManyBody().strength(-150))
    .force('center',    d3.forceCenter(W / 2, H / 2))
    .force('collision', d3.forceCollide(32));

  const link = svg.append('g')
    .selectAll('line').data(links).join('line')
    .attr('stroke',         d => d.kind === 'species' ? '#7A9E9F' : '#D4CFC8')
    .attr('stroke-width',   1.5)
    .attr('stroke-opacity', 0.8);

  const node = svg.append('g')
    .selectAll('g').data(nodes).join('g')
    .attr('cursor', d => d.isCurrent ? 'default' : 'pointer')
    .call(
      d3.drag()
        .on('start', (e, d) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
        .on('drag',  (e, d) => { d.fx = e.x; d.fy = e.y; })
        .on('end',   (e, d) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; })
    )
    .on('click', (e, d) => { if (!d.isCurrent) openModal(d.data); });

  node.append('circle')
    .attr('r',            d => d.isCurrent ? 13 : 8)
    .attr('fill',         d => d.isCurrent ? '#2B2B3B' : '#7A9E9F')
    .attr('fill-opacity', d => d.isCurrent ? 1 : 0.65);

  node.append('text')
    .text(d => d.label)
    .attr('x', d => d.isCurrent ? 17 : 12)
    .attr('y', 4)
    .attr('font-size',   '10px')
    .attr('fill',        '#2B2B3B')
    .attr('font-family', 'DM Sans, sans-serif');

  sim.on('tick', () => {
    link
      .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
    node.attr('transform', d => `translate(${
      Math.max(20, Math.min(W - 20, d.x))},${
      Math.max(20, Math.min(H - 20, d.y))})`);
  });
}

// ── Leaflet Map ───────────────────────────────────────────────────────────────

function renderMap(photo) {
  if (leafletMap) { leafletMap.remove(); leafletMap = null; }

  const container = document.getElementById('mapView');
  const lat = photo.lat ?? 25.04;
  const lng = photo.lng ?? 121.51;

  leafletMap = L.map(container, { zoomControl: true }).setView([lat, lng], 13);

  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OSM</a> © <a href="https://carto.com/">CARTO</a>',
    maxZoom: 19,
  }).addTo(leafletMap);

  const mainIcon = L.divIcon({
    html: `<div style="width:14px;height:14px;border-radius:50%;
           background:#2B2B3B;border:2px solid #F5EFE3;
           box-shadow:0 1px 5px rgba(0,0,0,.35)"></div>`,
    iconSize: [14, 14], iconAnchor: [7, 7], className: '',
  });
  const relIcon = L.divIcon({
    html: `<div style="width:9px;height:9px;border-radius:50%;
           background:#7A9E9F;border:1.5px solid #F5EFE3;
           box-shadow:0 1px 3px rgba(0,0,0,.2)"></div>`,
    iconSize: [9, 9], iconAnchor: [4.5, 4.5], className: '',
  });

  L.marker([lat, lng], { icon: mainIcon })
    .addTo(leafletMap)
    .bindPopup(photo.species_common_en || photo.species_scientific || photo.id)
    .openPopup();

  allPhotos
    .filter(p => p.id !== photo.id && p.lat && p.species_scientific === photo.species_scientific)
    .forEach(p =>
      L.marker([p.lat, p.lng], { icon: relIcon })
        .addTo(leafletMap)
        .bindPopup(p.species_common_en || p.id)
        .on('click', () => openModal(p))
    );
}

// ── Events ────────────────────────────────────────────────────────────────────

document.getElementById('modalClose').addEventListener('click', closeModal);

document.getElementById('modal').addEventListener('click', e => {
  if (e.target === document.getElementById('modal')) closeModal();
});

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeModal();
});

document.getElementById('tabGraph').addEventListener('click', () => {
  switchTab('graph');
  if (currentPhoto) renderGraph(currentPhoto);
});

document.getElementById('tabMap').addEventListener('click', () => {
  switchTab('map');
  if (currentPhoto) renderMap(currentPhoto);
});

init();
