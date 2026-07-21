import React, {
  useState,
  useMemo,
  useEffect,
} from "https://esm.sh/react@18?dev";
import { createRoot } from "https://esm.sh/react-dom@18/client?dev";

const h = React.createElement;

// ---------------------------------------------------------------------------
// Status colors and helpers
// ---------------------------------------------------------------------------

const STATUS_COLORS = {
  complete: "#22d3a0",
  running: "#f59e0b",
  failed: "#ef4444",
  pending: "#64748b",
};

function StatusBadge({ status }) {
  const color = STATUS_COLORS[status] || "#64748b";
  return h(
    "span",
    {
      style: {
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        padding: "2px 8px",
        borderRadius: 3,
        fontSize: 11,
        fontWeight: 600,
        letterSpacing: "0.06em",
        textTransform: "uppercase",
        background: color + "22",
        color: color,
        border: `1px solid ${color}44`,
      },
    },
    h("span", {
      style: { width: 5, height: 5, borderRadius: "50%", background: color },
    }),
    " ",
    status,
  );
}

function Tag({ label }) {
  return h(
    "span",
    {
      style: {
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: 3,
        fontSize: 11,
        fontWeight: 500,
        background: "#1e3a5f",
        color: "#7eb8f7",
        border: "1px solid #2a4f7a",
        marginRight: 6,
      },
    },
    label,
  );
}

function StatCard({ label, value, color }) {
  return h(
    "div",
    {
      style: {
        background: "#07131f",
        border: "1px solid #0d2035",
        borderRadius: 6,
        padding: "14px 16px",
      },
    },
    h(
      "div",
      {
        style: {
          fontSize: 10,
          color: "#2a5070",
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          marginBottom: 6,
        },
      },
      label,
    ),
    h(
      "div",
      {
        style: { fontSize: 24, fontWeight: 300, color: color || "#e2e8f0" },
      },
      value,
    ),
  );
}

// ---------------------------------------------------------------------------
// Case table
// ---------------------------------------------------------------------------

function CaseRow({ run, selected, onSelect }) {
  const fc = run.results?.force_coefficients;
  const rowStyle = {
    cursor: "pointer",
    borderBottom: "1px solid #0d2035",
    background: selected ? "#0f2a45" : "transparent",
  };
  const cellStyle = { padding: "8px 12px" };

  return h(
    "tr",
    {
      onClick: () => onSelect(run),
      style: rowStyle,
      onMouseEnter: (e) => {
        if (!selected) e.currentTarget.style.background = "#091929";
      },
      onMouseLeave: (e) => {
        if (!selected) e.currentTarget.style.background = "transparent";
      },
    },
    h(
      "td",
      {
        style: {
          ...cellStyle,
          fontFamily: "monospace",
          fontSize: 12,
          color: "#4a7a9b",
        },
      },
      run.case_id.slice(0, 8),
    ),
    h("td", { style: cellStyle }, h(StatusBadge, { status: run.status })),
    h(
      "td",
      { style: { ...cellStyle, fontSize: 12, color: "#7eb8f7" } },
      "Fr=" + (run.inputs?.froude_num ?? "?"),
    ),
    h(
      "td",
      { style: { ...cellStyle, fontSize: 12, color: "#7eb8f7" } },
      (run.inputs?.angle_of_attack ?? "?") + "°",
    ),
    h(
      "td",
      { style: { ...cellStyle, fontSize: 13, color: "#e2e8f0" } },
      fc ? fc.lift_coefficient.toFixed(4) : "—",
    ),
    h(
      "td",
      { style: { ...cellStyle, fontSize: 13, color: "#e2e8f0" } },
      fc ? fc.drag_coefficient.toFixed(4) : "—",
    ),
    h(
      "td",
      { style: { ...cellStyle, fontSize: 13, color: "#94a3b8" } },
      fc ? fc.lift_to_drag_ratio.toFixed(1) : "—",
    ),
    h(
      "td",
      { style: { ...cellStyle, fontSize: 11, color: "#4a6a8a" } },
      run.duration_seconds ? run.duration_seconds.toFixed(2) + "s" : "—",
    ),
  );
}

function CaseDetail({ run, onClose }) {
  const fc = run.results?.force_coefficients;

  const KV = ({ k, v, accent }) =>
    h(
      "div",
      {
        style: {
          display: "flex",
          justifyContent: "space-between",
          marginBottom: 6,
        },
      },
      h(
        "span",
        { style: { fontSize: 11, color: "#4a6a8a", fontFamily: "monospace" } },
        k,
      ),
      h(
        "span",
        { style: { fontSize: 12, color: accent || "#e2e8f0" } },
        v ?? "—",
      ),
    );

  const Section = ({ title, children }) =>
    h(
      "div",
      { style: { marginBottom: 24 } },
      h(
        "div",
        {
          style: {
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            color: "#2a5070",
            marginBottom: 10,
            paddingBottom: 6,
            borderBottom: "1px solid #0d2035",
          },
        },
        title,
      ),
      children,
    );

  return h(
    "div",
    {
      style: {
        position: "fixed",
        right: 0,
        top: 0,
        bottom: 0,
        width: 360,
        background: "#07131f",
        borderLeft: "1px solid #1a3050",
        padding: "24px 20px",
        overflowY: "auto",
        zIndex: 100,
        boxShadow: "-8px 0 32px rgba(0,0,0,0.4)",
      },
    },
    h(
      "div",
      {
        style: {
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 20,
        },
      },
      h(
        "span",
        { style: { fontSize: 11, color: "#4a7a9b", fontFamily: "monospace" } },
        run.case_id.slice(0, 12),
      ),
      h(
        "button",
        {
          onClick: onClose,
          style: {
            background: "none",
            border: "none",
            color: "#4a7a9b",
            cursor: "pointer",
            fontSize: 16,
          },
        },
        "✕",
      ),
    ),
    h(
      Section,
      { title: "Inputs" },
      Object.entries(run.inputs || {}).map(([k, v]) =>
        h(KV, { key: k, k: k, v: String(v) }),
      ),
    ),
    h(
      Section,
      { title: "Results" },
      fc
        ? [
            h(KV, {
              key: "cl",
              k: "lift_coefficient",
              v: fc.lift_coefficient.toFixed(6),
              accent: "#22d3a0",
            }),
            h(KV, {
              key: "cd",
              k: "drag_coefficient",
              v: fc.drag_coefficient.toFixed(6),
              accent: "#f59e0b",
            }),
            h(KV, {
              key: "ld",
              k: "L/D ratio",
              v: fc.lift_to_drag_ratio.toFixed(3),
            }),
          ]
        : h(
            "span",
            { style: { color: "#4a6a8a", fontSize: 12 } },
            "No results",
          ),
    ),
    h(
      Section,
      { title: "Environment" },
      h(KV, { k: "conda_env", v: run.environment?.conda_env }),
      h(KV, { k: "python", v: run.environment?.python_version }),
      h(KV, { k: "platform", v: run.environment?.platform }),
    ),
    h(
      Section,
      { title: "Timing" },
      h(KV, {
        k: "duration",
        v: run.duration_seconds ? run.duration_seconds.toFixed(3) + "s" : "—",
      }),
      h(KV, { k: "status", v: run.status }),
    ),
  );
}

// ---------------------------------------------------------------------------
// Generate demo data
// ---------------------------------------------------------------------------

function generateDemoData() {
  const runs = [];
  const froude_nums = [0.3, 0.5, 0.8, 1.2];
  const aoas = [0.0, 5.0, 10.0];

  for (let i = 0; i < 12; i++) {
    const fn = froude_nums[Math.floor(i / 3)];
    const aoa = aoas[i % 3];
    const alpha = (aoa * Math.PI) / 180;
    const cl = 2 * Math.PI * alpha;
    const cd = Math.max(0.001, 0.002 + (cl * cl) / (Math.PI * 8));

    runs.push({
      case_id: (i * 0x1a3f + 0x7c2b).toString(16).padStart(8, "0") + "cafe",
      handler: "PlaningPlateCase",
      inputs: { froude_num: fn, angle_of_attack: aoa, chord_length: 1.0 },
      status: "complete",
      duration_seconds: 0.8 + Math.random() * 0.4,
      results: {
        force_coefficients: {
          lift_coefficient: parseFloat(cl.toFixed(4)),
          drag_coefficient: parseFloat(cd.toFixed(4)),
          lift_to_drag_ratio: parseFloat((cl / cd).toFixed(2)),
        },
      },
      environment: {
        conda_env: "lembas-dev",
        python_version: "3.12.3",
        platform: "macOS-14.5",
      },
    });
  }

  return {
    study_id: "demo123",
    meta: {
      name: "planing-plate-froude-sweep",
      description:
        "Parametric study of a planing flat plate across Froude numbers and angles of attack",
      tags: ["hydrodynamics", "planing", "parametric"],
      plugins: ["lembas-planing-plate>=0.1.0"],
    },
    pushed_at: new Date().toISOString(),
    pushed_by: "demo",
    runs: runs,
  };
}

// ---------------------------------------------------------------------------
// Main App
// ---------------------------------------------------------------------------

function App() {
  const [study, setStudy] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedRun, setSelectedRun] = useState(null);
  const [sortKey, setSortKey] = useState("froude_num");
  const [filterStatus, setFilterStatus] = useState("all");

  // Fetch study data on mount
  useEffect(() => {
    const studyId = window.LEMBAS_STUDY_ID;

    if (studyId && studyId !== "demo") {
      fetch("/api/studies/" + studyId + "/detail")
        .then(function (r) {
          if (!r.ok) throw new Error("Study not found");
          return r.json();
        })
        .then(function (data) {
          setStudy(data);
          setLoading(false);
        })
        .catch(function (err) {
          setError(err.message);
          setLoading(false);
        });
    } else {
      // Demo mode
      setStudy(generateDemoData());
      setLoading(false);
    }
  }, []);

  // Compute sorted/filtered runs - always call useMemo, handle null inside
  const sortedRuns = useMemo(
    function () {
      if (!study || !study.runs) return [];

      let runs = study.runs.slice();

      if (filterStatus !== "all") {
        runs = runs.filter(function (r) {
          return r.status === filterStatus;
        });
      }

      runs.sort(function (a, b) {
        const aFr = a.inputs?.froude_num ?? 0;
        const bFr = b.inputs?.froude_num ?? 0;
        const aAoa = a.inputs?.angle_of_attack ?? 0;
        const bAoa = b.inputs?.angle_of_attack ?? 0;
        const aCl = a.results?.force_coefficients?.lift_coefficient ?? 0;
        const bCl = b.results?.force_coefficients?.lift_coefficient ?? 0;

        if (sortKey === "froude_num") return aFr - bFr;
        if (sortKey === "angle_of_attack") return aAoa - bAoa;
        if (sortKey === "cl") return bCl - aCl;
        return 0;
      });

      return runs;
    },
    [study, sortKey, filterStatus],
  );

  // Compute status counts - always call useMemo
  const statusCounts = useMemo(
    function () {
      if (!study || !study.runs) return {};

      const c = {};
      study.runs.forEach(function (r) {
        c[r.status] = (c[r.status] || 0) + 1;
      });
      return c;
    },
    [study],
  );

  // Loading state
  if (loading) {
    return h(
      "div",
      {
        style: {
          padding: 40,
          color: "#4a7a9b",
          fontFamily: "monospace",
          background: "#060f1a",
          minHeight: "100vh",
        },
      },
      "Loading...",
    );
  }

  // Error state
  if (error) {
    return h(
      "div",
      {
        style: {
          padding: 40,
          color: "#ef4444",
          fontFamily: "monospace",
          background: "#060f1a",
          minHeight: "100vh",
        },
      },
      "Error: " + error,
    );
  }

  // No data state
  if (!study) {
    return h(
      "div",
      {
        style: {
          padding: 40,
          color: "#4a7a9b",
          fontFamily: "monospace",
          background: "#060f1a",
          minHeight: "100vh",
        },
      },
      "No study data",
    );
  }

  const colStyle = {
    padding: "8px 12px",
    fontSize: 11,
    color: "#2a5070",
    fontWeight: 600,
    letterSpacing: "0.06em",
    textTransform: "uppercase",
    textAlign: "left",
    borderBottom: "2px solid #0d2035",
  };

  // Build status filter buttons
  const filterButtons = ["all", "complete", "failed", "pending"].map(
    function (s) {
      return h(
        "button",
        {
          key: s,
          onClick: function () {
            setFilterStatus(s);
          },
          style: {
            padding: "2px 8px",
            fontSize: 10,
            border: "1px solid " + (filterStatus === s ? "#22d3a0" : "#1a3050"),
            background: filterStatus === s ? "#0e2a40" : "none",
            color: filterStatus === s ? "#22d3a0" : "#4a6a8a",
            borderRadius: 3,
            cursor: "pointer",
          },
        },
        s,
      );
    },
  );

  // Build sort buttons
  const sortButtons = ["froude_num", "angle_of_attack", "cl"].map(function (k) {
    return h(
      "button",
      {
        key: k,
        onClick: function () {
          setSortKey(k);
        },
        style: {
          marginLeft: 6,
          padding: "1px 6px",
          fontSize: 10,
          background: sortKey === k ? "#0e2a40" : "none",
          border: "1px solid " + (sortKey === k ? "#7eb8f7" : "#1a3050"),
          color: sortKey === k ? "#7eb8f7" : "#2a5070",
          borderRadius: 3,
          cursor: "pointer",
        },
      },
      k,
    );
  });

  // Build stat cards
  const statCards = [
    h(StatCard, {
      key: "total",
      label: "Total Cases",
      value: study.runs.length,
    }),
  ];
  Object.keys(statusCounts).forEach(function (s) {
    statCards.push(
      h(StatCard, {
        key: s,
        label: s,
        value: statusCounts[s],
        color: STATUS_COLORS[s],
      }),
    );
  });

  // Build table rows
  const tableRows = sortedRuns.map(function (run) {
    return h(CaseRow, {
      key: run.case_id,
      run: run,
      selected: selectedRun?.case_id === run.case_id,
      onSelect: function (r) {
        setSelectedRun(selectedRun?.case_id === r.case_id ? null : r);
      },
    });
  });

  // Build tags
  const tags = (study.meta.tags || []).map(function (t) {
    return h(Tag, { key: t, label: t });
  });

  // Build table headers
  const tableHeaders = [
    "ID",
    "Status",
    "Froude",
    "AoA",
    "CL",
    "CD",
    "L/D",
    "Time",
  ].map(function (hdr) {
    return h("th", { key: hdr, style: colStyle }, hdr);
  });

  return h(
    "div",
    {
      style: {
        minHeight: "100vh",
        background: "#060f1a",
        color: "#c8d8e8",
        fontFamily: "'IBM Plex Mono', monospace",
        paddingRight: selectedRun ? 360 : 0,
        transition: "padding-right 0.2s",
      },
    },
    // Google Fonts
    h("link", {
      href: "https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&display=swap",
      rel: "stylesheet",
    }),

    // Top bar
    h(
      "div",
      {
        style: {
          padding: "0 32px",
          height: 48,
          display: "flex",
          alignItems: "center",
          borderBottom: "1px solid #0d2035",
          gap: 16,
        },
      },
      h(
        "span",
        {
          style: {
            fontSize: 13,
            color: "#22d3a0",
            fontWeight: 600,
            letterSpacing: "0.08em",
          },
        },
        "LEMBAS",
      ),
      h("span", { style: { color: "#1a3050" } }, "›"),
      h("span", { style: { fontSize: 12, color: "#7eb8f7" } }, study.meta.name),
    ),

    // Main content
    h(
      "div",
      { style: { padding: "28px 32px 40px" } },

      // Header
      h(
        "div",
        { style: { marginBottom: 28 } },
        h(
          "div",
          {
            style: {
              display: "flex",
              alignItems: "baseline",
              gap: 12,
              marginBottom: 8,
            },
          },
          h(
            "h1",
            {
              style: {
                margin: 0,
                fontSize: 20,
                fontWeight: 500,
                color: "#e2e8f0",
              },
            },
            study.meta.name,
          ),
          h(
            "span",
            {
              style: {
                fontSize: 11,
                color: "#2a5070",
                fontFamily: "monospace",
              },
            },
            "#" + study.study_id.slice(0, 8),
          ),
        ),
        h(
          "p",
          { style: { margin: "0 0 12px", fontSize: 13, color: "#4a7a9b" } },
          study.meta.description,
        ),
        h("div", { style: { display: "flex", flexWrap: "wrap" } }, tags),
        h(
          "div",
          { style: { marginTop: 10, fontSize: 11, color: "#2a5070" } },
          "pushed by ",
          h("span", { style: { color: "#4a7a9b" } }, study.pushed_by),
          " · ",
          new Date(study.pushed_at).toLocaleString(),
        ),
      ),

      // Stats
      h(
        "div",
        {
          style: {
            display: "grid",
            gridTemplateColumns: "repeat(4, 1fr)",
            gap: 12,
            marginBottom: 28,
          },
        },
        statCards,
      ),

      // Cases table
      h(
        "div",
        {
          style: {
            background: "#07131f",
            border: "1px solid #0d2035",
            borderRadius: 6,
            overflow: "hidden",
          },
        },
        // Table header bar
        h(
          "div",
          {
            style: {
              padding: "12px 16px",
              borderBottom: "1px solid #0d2035",
              display: "flex",
              alignItems: "center",
              gap: 12,
            },
          },
          h(
            "span",
            {
              style: {
                fontSize: 12,
                fontWeight: 600,
                color: "#7eb8f7",
                letterSpacing: "0.04em",
              },
            },
            "CASES",
          ),
          h(
            "div",
            { style: { display: "flex", gap: 6, marginLeft: 4 } },
            filterButtons,
          ),
          h(
            "div",
            { style: { marginLeft: "auto", fontSize: 11, color: "#2a5070" } },
            "sort by ",
            sortButtons,
          ),
        ),

        // Table
        h(
          "div",
          { style: { overflowX: "auto" } },
          h(
            "table",
            { style: { width: "100%", borderCollapse: "collapse" } },
            h("thead", null, h("tr", null, tableHeaders)),
            h("tbody", null, tableRows),
          ),
        ),
      ),
    ),

    // Detail panel
    selectedRun
      ? h(CaseDetail, {
          run: selectedRun,
          onClose: function () {
            setSelectedRun(null);
          },
        })
      : null,
  );
}

// Mount the app
const container = document.getElementById("root");
const root = createRoot(container);
root.render(h(App));
