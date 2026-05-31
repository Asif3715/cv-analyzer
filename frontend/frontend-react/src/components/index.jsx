import { useState } from "react";

export function FileIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="icon">
      <path d="M7 2h7l5 5v15a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z" fill="none" stroke="currentColor" strokeWidth="1.75" />
      <path d="M14 2v5h5" fill="none" stroke="currentColor" strokeWidth="1.75" />
    </svg>
  );
}

export function NavIcon({ id }) {
  const p = { fill: "none", stroke: "currentColor", strokeWidth: "1.75", strokeLinecap: "round", strokeLinejoin: "round" };
  const icons = {
    upload: <><path d="M12 16V6" {...p} /><path d="m8 10 4-4 4 4" {...p} /><path d="M5 18h14" {...p} /></>,
    documents: <><path d="M6 4h12v16H6z" {...p} /><path d="M9 8h6M9 12h6M9 16h4" {...p} /></>,
    analysis: <><path d="M5 19V9" {...p} /><path d="M11 19V5" {...p} /><path d="M17 19v-8" {...p} /><path d="M3 19h18" {...p} /></>,
  };
  return <svg viewBox="0 0 24 24" aria-hidden="true" className="icon">{icons[id]}</svg>;
}

export function ModuleIcon({ id }) {
  const p = { fill: "none", stroke: "currentColor", strokeWidth: "1.75", strokeLinecap: "round", strokeLinejoin: "round" };
  const icons = {
    education: <><path d="M12 3 2 8l10 5 8-4v6" {...p} /><path d="M6 10.5V15c0 1.2 2.7 3 6 3s6-1.8 6-3v-4.5" {...p} /></>,
    skills: <><path d="M10 6h10M4 6h2M10 12h10M4 12h2M10 18h10M4 18h2" {...p} /></>,
    experience: <><path d="M4 8h16v10H4z" {...p} /><path d="M9 8V6a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2" {...p} /></>,
    research: <><path d="M10 4a6 6 0 1 1 0 12 6 6 0 0 1 0-12z" {...p} /><path d="m15 15 5 5" {...p} /></>,
    supervision: <><path d="M4 18c1.5-3 4-5 8-5s6.5 2 8 5" {...p} /><path d="M8 10a4 4 0 1 1 8 0 4 4 0 0 1-8 0z" {...p} /></>,
    awards: <path d="M12 15 8.5 17l.8-4.1L6 10l4.2-.6L12 5.5l1.8 3.9 4.2.6-3.3 2.9.8 4.1z" {...p} />,
    books_patents: <><path d="M5 4h9a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3V4z" {...p} /><path d="M14 7h5v13" {...p} /></>,
  };
  return <svg viewBox="0 0 24 24" aria-hidden="true" className="icon iconSm">{icons[id]}</svg>;
}

export function PageHeader({ title, description, actions }) {
  return (
    <header className="pageHeader">
      <div className="pageHeaderText">
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {actions && <div className="pageHeaderActions">{actions}</div>}
    </header>
  );
}

export function Section({ title, description, children, variant = "default" }) {
  return (
    <section className={`section section--${variant}`}>
      {(title || description) && (
        <header className="sectionHead">
          {title && <h3 className="sectionTitle">{title}</h3>}
          {description && <p className="sectionDesc">{description}</p>}
        </header>
      )}
      <div className="sectionBody">{children}</div>
    </section>
  );
}

export function SummaryTile({ label, value, hint }) {
  return (
    <div className="metric">
      <span className="metricLabel">{label}</span>
      <span className="metricValue">{value}</span>
      {hint && <span className="metricHint">{hint}</span>}
    </div>
  );
}

export function DataTable({ columns, rows, emptyMessage = "No records", getRowKey }) {
  if (!rows?.length) {
    return <div className="tableEmpty">{emptyMessage}</div>;
  }
  return (
    <div className="tableWrap">
      <table className="dataTable">
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col.key}>{col.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={getRowKey ? getRowKey(row, i) : i}>
              {columns.map((col) => (
                <td key={col.key}>{col.render ? col.render(row) : row[col.key] ?? "—"}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function statusClass(status) {
  const s = (status || "missing").toLowerCase();
  if (["answered", "present", "verified", "strong"].includes(s)) return "positive";
  if (["insufficient_data", "missing", "unclear", "unverified"].includes(s)) return "neutral";
  if (["failed", "weak"].includes(s)) return "negative";
  return "neutral";
}

export function AssessmentHero({ label, strength, confidence, summary, meta }) {
  const pct = Math.round(Math.min(100, Math.max(0, Number(confidence) * (Number(confidence) <= 1 ? 100 : 1))));
  return (
    <div className="assessmentHero">
      <div className="assessmentHeroTop">
        <div>
          <span className="overline">{label || "AI assessment"}</span>
          <div className="assessmentHeroTitle">
            {strength ? (
              <span className={`strengthPill strengthPill--${statusClass(strength)}`}>{strength}</span>
            ) : (
              <span className="strengthPill strengthPill--neutral">Pending</span>
            )}
          </div>
        </div>
        <div className="confidenceBlock">
          <span className="confidenceLabel">Confidence</span>
          <div className="confidenceTrack">
            <div className="confidenceFill" style={{ width: `${pct}%` }} />
          </div>
          <span className="confidenceValue">{confidence ?? 0}</span>
        </div>
      </div>
      {summary && <p className="assessmentSummary">{summary}</p>}
      {meta?.length > 0 && (
        <div className="assessmentMeta">
          {meta.map((item) => (
            <span key={item.label}>
              {item.label} <strong>{item.value}</strong>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export function AnswerCardGrid({ answers, prefix }) {
  if (!answers?.length) return null;
  return (
    <div className="insightList">
      {answers.map((answer, index) => {
        const conf = answer.confidence ?? 0;
        const pct = Math.round(Math.min(100, Math.max(0, conf * (conf <= 1 ? 100 : 1))));
        const status = answer.status || "missing";
        return (
          <article className={`insightCard insightCard--${statusClass(status)}`} key={`${prefix}-${index}`}>
            <div className="insightCardAccent" aria-hidden="true" />
            <header className="insightHeader">
              <span className="insightIndex">Q{index + 1}</span>
              <span className={`statusChip statusChip--${statusClass(status)}`}>{status.replace(/_/g, " ")}</span>
            </header>
            <h4 className="insightQuestion">{answer.question || "Question"}</h4>
            <p className="insightAnswer">{answer.answer || "No answer returned."}</p>
            <footer className="insightFooter">
              <div className="insightConfidence">
                <span>Confidence</span>
                <div className="insightConfidenceBar">
                  <div style={{ width: `${pct}%` }} />
                </div>
                <strong>{conf}</strong>
              </div>
              {answer.evidence_fields?.length > 0 && (
                <div className="evidenceTags">
                  {answer.evidence_fields.map((field) => (
                    <span className="evidenceTag" key={field}>{field}</span>
                  ))}
                </div>
              )}
            </footer>
          </article>
        );
      })}
    </div>
  );
}

export function AnalysisToolbar({ onLoadFacts, onAnalyze, extra, loading, disabled, regen, onRegenChange }) {
  return (
    <div className="analysisToolbar">
      <div className="analysisToolbarPrimary">
        <button className="btn btnSecondary" type="button" onClick={onLoadFacts} disabled={loading || disabled}>
          Load facts
        </button>
        <button className="btn" type="button" onClick={onAnalyze} disabled={loading || disabled}>
          Run AI analysis
        </button>
        {extra}
      </div>
      {onRegenChange && (
        <label className="toggle analysisToolbarOptions">
          <input type="checkbox" checked={regen} onChange={(e) => onRegenChange(e.target.checked)} />
          Regenerate cached
        </label>
      )}
    </div>
  );
}

export function ModuleRail({ modules, activeId, onSelect }) {
  return (
    <nav className="moduleRail" aria-label="Analysis modules">
      {modules.map((module) => (
        <button
          key={module.id}
          type="button"
          className={`moduleRailItem ${activeId === module.id ? "active" : ""}`}
          onClick={() => onSelect(module.id)}
          title={module.description}
        >
          <ModuleIcon id={module.id} />
          <span className="moduleRailLabel">{module.label}</span>
        </button>
      ))}
    </nav>
  );
}

export function Sidebar({ brand, navItems, activeSection, onNavigate, candidates, selectedDocId, onSelectCandidate, activeCandidate }) {
  return (
    <aside className="sidebar">
      <div className="sidebarBrand">{brand}</div>

      <nav className="sidebarNav" aria-label="Main">
        {navItems.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`navItem ${activeSection === item.id ? "active" : ""}`}
            onClick={() => onNavigate(item.id)}
          >
            <NavIcon id={item.id} />
            <span className="navItemText">
              <span className="navItemLabel">{item.label}</span>
              <span className="navItemDesc">{item.description}</span>
            </span>
          </button>
        ))}
      </nav>

      {candidates.length > 0 && (
        <div className="sidebarCandidates">
          <div className="sidebarCandidatesHead">
            <span>Candidates</span>
            <span className="countBadge">{candidates.length}</span>
          </div>
          <ul className="candidateList">
            {candidates.slice(0, 12).map((doc) => (
              <li key={doc.document_id}>
                <button
                  type="button"
                  className={`candidateListItem ${selectedDocId === doc.document_id ? "active" : ""}`}
                  onClick={() => onSelectCandidate(doc.document_id)}
                >
                  <span className="candidateListName">{doc.candidate_name || doc.file_name}</span>
                  <span className={`statusDot statusDot--${doc.status}`} title={doc.status} />
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="sidebarFooter">
        {activeCandidate ? (
          <div className="activeCandidate">
            <div className="activeCandidateAvatar">
              {(activeCandidate.name || "?").charAt(0).toUpperCase()}
            </div>
            <div className="activeCandidateInfo">
              <span className="activeCandidateLabel">Selected</span>
              <strong>{activeCandidate.name}</strong>
              <span className="activeCandidateFile">{activeCandidate.file}</span>
            </div>
          </div>
        ) : (
          <p className="sidebarHint">Select a candidate to begin analysis</p>
        )}
      </div>
    </aside>
  );
}

export function EducationTrendChart({ rows }) {
  const [hovered, setHovered] = useState(null);
  const points = (rows || [])
    .map((row) => ({
      year: Number.parseInt(row.end_year, 10),
      value: Number(row.score_normalized_100),
      rawValue: Number.parseFloat(String(row.score_raw || "").replace(/[^0-9.]+/g, "")),
      rawLabel: row.score_raw || "missing",
      label: row.degree_title || row.level || "Education",
      institution: row.institution || "",
    }))
    .filter((point) => Number.isFinite(point.year) && Number.isFinite(point.value));

  if (points.length < 2) {
    return <div className="chartEmpty">Not enough normalized scores to plot a trend.</div>;
  }

  const width = 920;
  const height = 260;
  const padding = { top: 24, right: 24, bottom: 48, left: 56 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const sorted = [...points].sort((a, b) => a.year - b.year);
  const rawValues = sorted.map((p) => p.rawValue).filter(Number.isFinite);
  const hasRawSeries = rawValues.length >= 2;
  const rawMin = hasRawSeries ? Math.min(...rawValues) : 0;
  const rawMax = hasRawSeries ? Math.max(...rawValues) : 100;

  const xFor = (i) => padding.left + (sorted.length === 1 ? plotWidth / 2 : (plotWidth * i) / (sorted.length - 1));
  const yFor = (v) => padding.top + plotHeight - (Math.max(0, Math.min(100, v)) / 100) * plotHeight;
  const rawScaledYFor = (v) => {
    if (!Number.isFinite(v)) return null;
    const scaled = rawMax === rawMin ? 50 : ((v - rawMin) / (rawMax - rawMin)) * 100;
    return yFor(scaled);
  };

  const normalizedPath = sorted.map((p, i) => `${i === 0 ? "M" : "L"} ${xFor(i)} ${yFor(p.value)}`).join(" ");
  const rawPath = sorted
    .map((p, i) => {
      const y = rawScaledYFor(p.rawValue);
      return Number.isFinite(y) ? `${i === 0 ? "M" : "L"} ${xFor(i)} ${y}` : null;
    })
    .filter(Boolean)
    .join(" ");

  return (
    <div className="chart">
      <div className="chartTop">
        <div>
          <p className="overline">Score trend</p>
          <h4 className="chartTitle">Normalized education scores</h4>
        </div>
        <div className="chartLegend">
          <span><i className="legendDot primary" />Normalized</span>
          <span><i className="legendDot secondary" />Raw trend</span>
        </div>
      </div>
      <div className="chartBody">
        <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Education score trend">
          <defs>
            <linearGradient id="chartFill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="rgba(14, 165, 233, 0.22)" />
              <stop offset="100%" stopColor="rgba(14, 165, 233, 0)" />
            </linearGradient>
          </defs>
          {[0, 25, 50, 75, 100].map((tick) => {
            const y = yFor(tick);
            return (
              <g key={tick}>
                <line x1={padding.left} x2={width - padding.right} y1={y} y2={y} className="gridLine" />
                <text x={padding.left - 10} y={y + 4} textAnchor="end" className="axisLabel">{tick}</text>
              </g>
            );
          })}
          <path
            d={`${normalizedPath} L ${xFor(sorted.length - 1)} ${height - padding.bottom} L ${xFor(0)} ${height - padding.bottom} Z`}
            fill="url(#chartFill)"
          />
          <path d={normalizedPath} className="linePrimary" fill="none" />
          {hasRawSeries && <path d={rawPath} className="lineSecondary" fill="none" />}
          {sorted.map((point, i) => {
            const x = xFor(i);
            const y = yFor(point.value);
            const rawY = rawScaledYFor(point.rawValue);
            return (
              <g
                key={`${point.year}-${i}`}
                onMouseEnter={() =>
                  setHovered({ ...point, x, normalizedY: y, rawY, rawMin, rawMax, hasRawSeries })
                }
                onMouseLeave={() => setHovered(null)}
              >
                <circle cx={x} cy={y} r="5" className="dotPrimary" />
                {Number.isFinite(rawY) && <circle cx={x} cy={rawY} r="4" className="dotSecondary" />}
                <circle cx={x} cy={y} r="12" fill="transparent" />
                <text x={x} y={height - padding.bottom + 18} textAnchor="middle" className="axisLabel">
                  {point.year}
                </text>
              </g>
            );
          })}
        </svg>
        {hovered && (
          <div className="chartTip">
            <strong>{hovered.year} · {hovered.label}</strong>
            <span>{hovered.institution || "Institution not listed"}</span>
            <div className="chartTipRow"><span>Normalized</span><strong>{hovered.value}</strong></div>
            <div className="chartTipRow"><span>Raw</span><strong>{hovered.rawLabel}</strong></div>
          </div>
        )}
      </div>
    </div>
  );
}

export function EmptyState({ title, description, action }) {
  return (
    <div className="emptyState">
      <div className="emptyStateIcon" aria-hidden="true">◇</div>
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  );
}
