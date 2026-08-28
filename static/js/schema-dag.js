/**
 * Renders a step dependency DAG as an inline SVG into the given container element.
 * steps: Array of {name, requires: string[], has_condition: boolean, description: string}
 */
function renderStepDAG(container, steps) {
  if (!container || !steps || steps.length === 0) return;

  const stepMap = {};
  steps.forEach((s) => {
    stepMap[s.name] = s;
  });

  // Compute BFS levels from requires dependencies
  const levels = {};
  function getLevel(name) {
    if (levels[name] !== undefined) return levels[name];
    const step = stepMap[name];
    if (!step || step.requires.length === 0) {
      levels[name] = 0;
      return 0;
    }
    let max = -1;
    for (const req of step.requires) max = Math.max(max, getLevel(req));
    levels[name] = max + 1;
    return levels[name];
  }
  steps.forEach((s) => getLevel(s.name));

  // Group by level
  const groups = {};
  let maxLevel = 0;
  steps.forEach((s) => {
    const l = levels[s.name] || 0;
    if (!groups[l]) groups[l] = [];
    groups[l].push(s);
    maxLevel = Math.max(maxLevel, l);
  });

  const nW = 140,
    nH = 50,
    lGap = 80,
    nGap = 20;

  let svgWidth = 0;
  for (let l = 0; l <= maxLevel; l++) {
    const n = (groups[l] || []).length;
    svgWidth = Math.max(svgWidth, n * nW + (n - 1) * nGap);
  }
  svgWidth = Math.max(svgWidth + 40, 300);
  const svgHeight = (maxLevel + 1) * (nH + lGap) + 40;

  const pos = {};
  for (let l = 0; l <= maxLevel; l++) {
    const nodes = groups[l] || [];
    const lW = nodes.length * nW + (nodes.length - 1) * nGap;
    const startX = (svgWidth - lW) / 2;
    nodes.forEach((s, i) => {
      pos[s.name] = {
        x: startX + i * (nW + nGap) + nW / 2,
        y: 30 + l * (nH + lGap) + nH / 2,
      };
    });
  }

  let svg = `<svg width="${svgWidth}" height="${svgHeight}" style="display:block;">
    <defs>
      <marker id="arr" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
        <polygon points="0 0,10 3.5,0 7" fill="#4a6a8a"/>
      </marker>
    </defs>`;

  // Edges
  steps.forEach((s) => {
    const to = pos[s.name];
    if (!to) return;
    (s.requires || []).forEach((req) => {
      const from = pos[req];
      if (!from) return;
      svg += `<line x1="${from.x}" y1="${from.y + nH / 2}"
                    x2="${to.x}"   y2="${to.y - nH / 2 - 5}"
                    stroke="#4a6a8a" stroke-width="2" marker-end="url(#arr)"/>`;
    });
  });

  // Nodes
  steps.forEach((s) => {
    const p = pos[s.name];
    if (!p) return;
    const fill = s.has_condition ? "#1a2a3a" : "#0d2137";
    const stroke = s.has_condition ? "#f59e0b" : "#1e3a5f";
    const label = s.name.length > 18 ? s.name.slice(0, 17) + "…" : s.name;
    svg += `
      <rect x="${p.x - nW / 2}" y="${p.y - nH / 2}"
            width="${nW}" height="${nH}" rx="6"
            fill="${fill}" stroke="${stroke}" stroke-width="1.5"/>
      <text x="${p.x}" y="${p.y + 5}" text-anchor="middle"
            fill="#e0e0e0" font-size="12" font-family="monospace">${label}</text>`;
    if (s.has_condition) {
      svg += `<circle cx="${p.x + nW / 2 - 8}" cy="${p.y - nH / 2 + 8}"
                      r="4" fill="#f59e0b"/>`;
    }
  });

  svg += `</svg>`;
  container.innerHTML = svg;
}
