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
// Format helpers
// ---------------------------------------------------------------------------

function formatNumber(val) {
  if (val === null || val === undefined) return "—";
  if (typeof val !== "number") return String(val);
  if (Math.abs(val) < 0.01 || Math.abs(val) >= 10000) {
    return val.toExponential(2);
  }
  return val.toFixed(2);
}

function formatInput(key, val) {
  if (key === "froude_num") return "Fr=" + formatNumber(val);
  if (key === "angle_of_attack") return formatNumber(val) + "°";
  return formatNumber(val);
}

// ---------------------------------------------------------------------------
// Case table
// ---------------------------------------------------------------------------

function CaseRow({ run, selected, onSelect, resultKeys }) {
  const results = run.results || {};
  const inputs = run.inputs || {};
  const rowStyle = {
    cursor: "pointer",
    borderBottom: "1px solid #0d2035",
    background: selected ? "#0f2a45" : "transparent",
  };
  const cellStyle = { padding: "8px 12px" };

  // Build input cells - show first 2 inputs
  const inputKeys = Object.keys(inputs).slice(0, 2);
  const inputCells = inputKeys.map(function (k) {
    return h(
      "td",
      { key: k, style: { ...cellStyle, fontSize: 12, color: "#7eb8f7" } },
      formatInput(k, inputs[k]),
    );
  });

  // Build result cells - show first 3 result values
  const resultCells = resultKeys.slice(0, 3).map(function (k) {
    const val = results[k];
    return h(
      "td",
      { key: k, style: { ...cellStyle, fontSize: 13, color: "#e2e8f0" } },
      formatNumber(val),
    );
  });

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
    inputCells,
    resultCells,
    h(
      "td",
      { style: { ...cellStyle, fontSize: 11, color: "#4a6a8a" } },
      run.duration_seconds ? run.duration_seconds.toFixed(2) + "s" : "—",
    ),
  );
}

// ---------------------------------------------------------------------------
// File Browser Component
// ---------------------------------------------------------------------------

function FileBrowser({ studyId, caseId }) {
  const [manifest, setManifest] = useState(null);
  const [loading, setLoading] = useState(true);
  const [currentPath, setCurrentPath] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileContent, setFileContent] = useState(null);
  const [loadingContent, setLoadingContent] = useState(false);

  // Fetch manifest on mount
  useEffect(() => {
    fetch(`/api/storage/manifests/${studyId}/${caseId}`)
      .then((r) => {
        if (!r.ok) {
          if (r.status === 404) return { files: {} };
          throw new Error("Failed to load manifest");
        }
        return r.json();
      })
      .then((data) => {
        setManifest(data.files || {});
        setLoading(false);
      })
      .catch(() => {
        setManifest({});
        setLoading(false);
      });
  }, [studyId, caseId]);

  // Build directory tree from flat manifest
  const tree = useMemo(() => {
    if (!manifest) return { dirs: {}, files: {} };

    const result = { dirs: {}, files: {} };

    Object.keys(manifest).forEach((path) => {
      const parts = path.split("/");
      let current = result;

      for (let i = 0; i < parts.length - 1; i++) {
        const dir = parts[i];
        if (!current.dirs[dir]) {
          current.dirs[dir] = { dirs: {}, files: {} };
        }
        current = current.dirs[dir];
      }

      const filename = parts[parts.length - 1];
      current.files[filename] = { path, hash: manifest[path] };
    });

    return result;
  }, [manifest]);

  // Get current directory contents
  const currentDir = useMemo(() => {
    if (!currentPath) return tree;

    const parts = currentPath.split("/").filter(Boolean);
    let current = tree;

    for (const part of parts) {
      if (current.dirs[part]) {
        current = current.dirs[part];
      } else {
        return { dirs: {}, files: {} };
      }
    }

    return current;
  }, [tree, currentPath]);

  // Fetch file content
  const loadFileContent = async (fileInfo) => {
    setSelectedFile(fileInfo);
    setLoadingContent(true);
    setFileContent(null);

    try {
      const response = await fetch(`/api/storage/blobs/${fileInfo.hash}`);
      if (!response.ok) throw new Error("Failed to load file");

      const text = await response.text();
      setFileContent(text);
    } catch {
      setFileContent("(Failed to load file content)");
    } finally {
      setLoadingContent(false);
    }
  };

  if (loading) {
    return h(
      "div",
      { style: { color: "#4a6a8a", fontSize: 11 } },
      "Loading files...",
    );
  }

  const dirNames = Object.keys(currentDir.dirs).sort();
  const fileNames = Object.keys(currentDir.files).sort();

  if (dirNames.length === 0 && fileNames.length === 0) {
    return h(
      "div",
      { style: { color: "#4a6a8a", fontSize: 11 } },
      "No files synced",
    );
  }

  const itemStyle = {
    padding: "4px 8px",
    fontSize: 11,
    fontFamily: "monospace",
    cursor: "pointer",
    borderRadius: 3,
    display: "flex",
    alignItems: "center",
    gap: 6,
  };

  const breadcrumbs = currentPath
    ? h(
        "div",
        {
          style: {
            display: "flex",
            alignItems: "center",
            gap: 4,
            marginBottom: 8,
            fontSize: 10,
            color: "#4a6a8a",
          },
        },
        h(
          "span",
          {
            style: { cursor: "pointer", color: "#7eb8f7" },
            onClick: () => {
              setCurrentPath("");
              setSelectedFile(null);
              setFileContent(null);
            },
          },
          "root",
        ),
        currentPath
          .split("/")
          .filter(Boolean)
          .map((part, i, arr) =>
            h(
              React.Fragment,
              { key: i },
              h("span", { style: { color: "#1a3050" } }, "/"),
              h(
                "span",
                {
                  style: {
                    cursor: "pointer",
                    color: i === arr.length - 1 ? "#e2e8f0" : "#7eb8f7",
                  },
                  onClick: () => {
                    const newPath = arr.slice(0, i + 1).join("/");
                    setCurrentPath(newPath);
                    setSelectedFile(null);
                    setFileContent(null);
                  },
                },
                part,
              ),
            ),
          ),
      )
    : null;

  const dirItems = dirNames.map((name) =>
    h(
      "div",
      {
        key: "d-" + name,
        style: { ...itemStyle, color: "#7eb8f7" },
        onClick: () => {
          setCurrentPath(currentPath ? currentPath + "/" + name : name);
          setSelectedFile(null);
          setFileContent(null);
        },
        onMouseEnter: (e) => (e.currentTarget.style.background = "#0e2a40"),
        onMouseLeave: (e) => (e.currentTarget.style.background = "transparent"),
      },
      h("span", null, "📁"),
      name,
    ),
  );

  const fileItems = fileNames.map((name) => {
    const fileInfo = { name, ...currentDir.files[name] };
    const isSelected = selectedFile?.path === fileInfo.path;

    return h(
      "div",
      {
        key: "f-" + name,
        style: {
          ...itemStyle,
          color: isSelected ? "#22d3a0" : "#e2e8f0",
          background: isSelected ? "#0e2a40" : "transparent",
        },
        onClick: () => loadFileContent(fileInfo),
        onMouseEnter: (e) => {
          if (!isSelected) e.currentTarget.style.background = "#091929";
        },
        onMouseLeave: (e) => {
          if (!isSelected) e.currentTarget.style.background = "transparent";
        },
      },
      h("span", null, "📄"),
      name,
    );
  });

  const filePreview = selectedFile
    ? h(
        "div",
        {
          style: {
            marginTop: 12,
            padding: 10,
            background: "#060f1a",
            border: "1px solid #0d2035",
            borderRadius: 4,
            maxHeight: 200,
            overflowY: "auto",
          },
        },
        h(
          "div",
          {
            style: {
              fontSize: 10,
              color: "#4a6a8a",
              marginBottom: 6,
              fontFamily: "monospace",
            },
          },
          selectedFile.name,
        ),
        loadingContent
          ? h(
              "div",
              { style: { color: "#4a6a8a", fontSize: 11 } },
              "Loading...",
            )
          : h(
              "pre",
              {
                style: {
                  margin: 0,
                  fontSize: 10,
                  color: "#c8d8e8",
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-all",
                  fontFamily: "monospace",
                  lineHeight: 1.4,
                },
              },
              fileContent?.slice(0, 4000) +
                (fileContent?.length > 4000 ? "\n..." : ""),
            ),
      )
    : null;

  return h(
    "div",
    null,
    breadcrumbs,
    h(
      "div",
      { style: { maxHeight: 180, overflowY: "auto" } },
      dirItems,
      fileItems,
    ),
    filePreview,
  );
}

function CaseDetail({ run, studyId, onClose }) {
  const results = run.results || {};
  const inputs = run.inputs || {};

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

  // Build results display
  const resultKeys = Object.keys(results);
  const resultColors = ["#22d3a0", "#f59e0b", "#7eb8f7", "#e879f9"];
  const resultsContent =
    resultKeys.length > 0
      ? resultKeys.map(function (k, i) {
          return h(KV, {
            key: k,
            k: k,
            v: formatNumber(results[k]),
            accent: resultColors[i % resultColors.length],
          });
        })
      : h("span", { style: { color: "#4a6a8a", fontSize: 12 } }, "No results");

  return h(
    "div",
    {
      style: {
        position: "fixed",
        right: 0,
        top: 0,
        bottom: 0,
        width: 400,
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
      Object.entries(inputs).map(([k, v]) =>
        h(KV, { key: k, k: k, v: formatNumber(v) }),
      ),
    ),
    h(Section, { title: "Results" }, resultsContent),
    h(
      Section,
      { title: "Files" },
      h(FileBrowser, { studyId: studyId, caseId: run.case_id }),
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
// Main App
// ---------------------------------------------------------------------------

function App() {
  const [study, setStudy] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedRun, setSelectedRun] = useState(null);
  const [sortKey, setSortKey] = useState(null);
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
      // Demo mode - generate data matching real structure
      const runs = [];
      const froude_nums = [0.5, 1.0, 1.5, 2.0];
      const aoas = [5.0, 7.5, 10.0, 12.5, 15.0];

      froude_nums.forEach(function (fn) {
        aoas.forEach(function (aoa) {
          runs.push({
            case_id:
              Math.random().toString(16).slice(2, 10) +
              Math.random().toString(16).slice(2, 10),
            handler: "PlaningPlateCase",
            inputs: { froude_num: fn, angle_of_attack: aoa },
            status: "complete",
            duration_seconds: 0.001 + Math.random() * 0.002,
            results: {
              drag: 5 + fn * 10 + aoa * 3 + Math.random() * 2,
              lift: 50 + fn * 20 + aoa * 10 + Math.random() * 5,
              moment: -10 - fn * 2 - aoa * 0.5 + Math.random() * 2,
            },
            environment: {},
          });
        });
      });

      setStudy({
        study_id: "demo123456789",
        meta: {
          name: "planing-plate-froude-sweep",
          description:
            "Parametric study of planing flat plate across Froude numbers and angles of attack",
          tags: ["hydrodynamics", "planing", "parametric"],
          plugins: [],
        },
        pushed_at: new Date().toISOString(),
        pushed_by: "demo",
        runs: runs,
      });
      setLoading(false);
    }
  }, []);

  // Discover input and result keys from the data
  const { inputKeys, resultKeys } = useMemo(
    function () {
      if (!study || !study.runs || study.runs.length === 0) {
        return { inputKeys: [], resultKeys: [] };
      }
      const firstRun = study.runs[0];
      return {
        inputKeys: Object.keys(firstRun.inputs || {}),
        resultKeys: Object.keys(firstRun.results || {}),
      };
    },
    [study],
  );

  // Default sort key to first input
  useEffect(
    function () {
      if (!sortKey && inputKeys.length > 0) {
        setSortKey(inputKeys[0]);
      }
    },
    [inputKeys, sortKey],
  );

  // Compute sorted/filtered runs
  const sortedRuns = useMemo(
    function () {
      if (!study || !study.runs) return [];

      let runs = study.runs.slice();

      if (filterStatus !== "all") {
        runs = runs.filter(function (r) {
          return r.status === filterStatus;
        });
      }

      if (sortKey) {
        runs.sort(function (a, b) {
          // Try inputs first
          if (a.inputs && a.inputs[sortKey] !== undefined) {
            return (a.inputs[sortKey] || 0) - (b.inputs[sortKey] || 0);
          }
          // Try results
          if (a.results && a.results[sortKey] !== undefined) {
            return (b.results[sortKey] || 0) - (a.results[sortKey] || 0);
          }
          return 0;
        });
      }

      return runs;
    },
    [study, sortKey, filterStatus],
  );

  // Compute status counts
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

  // Build sort buttons from inputs + results
  const sortOptions = inputKeys.slice(0, 2).concat(resultKeys.slice(0, 2));
  const sortButtons = sortOptions.map(function (k) {
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
      resultKeys: resultKeys,
    });
  });

  // Build tags
  const tags = (study.meta.tags || []).map(function (t) {
    return h(Tag, { key: t, label: t });
  });

  // Build table headers dynamically
  const inputHeaders = inputKeys.slice(0, 2).map(function (k) {
    return h("th", { key: k, style: colStyle }, k);
  });
  const resultHeaders = resultKeys.slice(0, 3).map(function (k) {
    return h("th", { key: k, style: colStyle }, k);
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
        "a",
        {
          href: "/studies",
          style: {
            fontSize: 13,
            color: "#22d3a0",
            fontWeight: 600,
            letterSpacing: "0.08em",
            textDecoration: "none",
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
          h("span", { style: { color: "#4a7a9b" } }, study.pushed_by || "—"),
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
            h(
              "thead",
              null,
              h(
                "tr",
                null,
                h("th", { style: colStyle }, "ID"),
                h("th", { style: colStyle }, "Status"),
                inputHeaders,
                resultHeaders,
                h("th", { style: colStyle }, "Time"),
              ),
            ),
            h("tbody", null, tableRows),
          ),
        ),
      ),
    ),

    // Detail panel
    selectedRun
      ? h(CaseDetail, {
          run: selectedRun,
          studyId: study.study_id,
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
