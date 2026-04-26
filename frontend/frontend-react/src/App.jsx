import { useEffect, useMemo, useRef, useState } from "react";
import {
  analyzeBooksPatents,
  analyzeExperience,
  analyzeResearch,
  analyzeSkills,
  analyzeEducation,
  api,
  getBooksPatents,
  getBooksPatentsFacts,
  getDocument,
  getEducationFacts,
  getExperienceFacts,
  getSupervision,
  getSupervisionFacts,
  analyzeSupervision,
  getResearchFacts,
  getSkillsFacts,
  listDocuments,
  reprocessDocument,
  recheckUnverifiedResearch,
  uploadCVs
} from "./api";

const logoUrl = "/logo.svg";

function FileIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="fileIcon">
      <path d="M7 2h7l5 5v15a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <path d="M14 2v5h5" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <path d="M9 13h6M9 17h6" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function CvIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="cvIcon">
      <path d="M6 3h8l4 4v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <path d="M14 3v5h5" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <path d="M8 12h8M8 16h5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function NavIcon({ id }) {
  const common = { fill: "none", stroke: "currentColor", strokeWidth: "1.8", strokeLinecap: "round", strokeLinejoin: "round" };
  switch (id) {
    case "upload":
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true" className="navIcon">
          <path d="M12 16V6" {...common} />
          <path d="m8 10 4-4 4 4" {...common} />
          <path d="M5 18h14" {...common} />
        </svg>
      );
    case "documents":
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true" className="navIcon">
          <path d="M6 4h12v16H6z" {...common} />
          <path d="M9 8h6M9 12h6M9 16h4" {...common} />
        </svg>
      );
    case "analysis":
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true" className="navIcon">
          <path d="M5 19V9" {...common} />
          <path d="M11 19V5" {...common} />
          <path d="M17 19v-8" {...common} />
          <path d="M3 19h18" {...common} />
        </svg>
      );
    default:
      return null;
  }
}

function ModuleIcon({ id }) {
  const common = { fill: "none", stroke: "currentColor", strokeWidth: "1.8", strokeLinecap: "round", strokeLinejoin: "round" };
  switch (id) {
    case "education":
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true" className="moduleIcon">
          <path d="M12 3 2 8l10 5 8-4v6" {...common} />
          <path d="M6 10.5V15c0 1.2 2.7 3 6 3s6-1.8 6-3v-4.5" {...common} />
        </svg>
      );
    case "skills":
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true" className="moduleIcon">
          <path d="M10 6h10" {...common} />
          <path d="M4 6h2" {...common} />
          <path d="M10 12h10" {...common} />
          <path d="M4 12h2" {...common} />
          <path d="M10 18h10" {...common} />
          <path d="M4 18h2" {...common} />
        </svg>
      );
    case "experience":
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true" className="moduleIcon">
          <path d="M4 8h16v10H4z" {...common} />
          <path d="M9 8V6a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2" {...common} />
        </svg>
      );
    case "research":
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true" className="moduleIcon">
          <path d="M10 4a6 6 0 1 1 0 12 6 6 0 0 1 0-12z" {...common} />
          <path d="m15 15 5 5" {...common} />
        </svg>
      );
    case "supervision":
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true" className="moduleIcon">
          <path d="M4 18c1.5-3 4-5 8-5s6.5 2 8 5" {...common} />
          <path d="M8 10a4 4 0 1 1 8 0 4 4 0 0 1-8 0z" {...common} />
        </svg>
      );
    case "awards":
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true" className="moduleIcon">
          <path d="M12 15 8.5 17l.8-4.1L6 10l4.2-.6L12 5.5l1.8 3.9 4.2.6-3.3 2.9.8 4.1z" {...common} />
        </svg>
      );
    case "books_patents":
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true" className="moduleIcon">
          <path d="M5 4h9a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3V4z" {...common} />
          <path d="M14 7h5v13" {...common} />
        </svg>
      );
    default:
      return null;
  }
}

function prettyJson(value) {
  return JSON.stringify(value, null, 2);
}

function SummaryTile({ label, value }) {
  return (
    <div className="tile">
      <div className="tileLabel">{label}</div>
      <div className="tileValue">{value}</div>
    </div>
  );
}

function AnswerCardGrid({ answers, prefix }) {
  if (!answers || answers.length === 0) {
    return null;
  }

  return (
    <div className="answerGrid">
      {answers.map((answer, index) => (
        <article className="answerCard" key={`${prefix}-${index}`}>
          <div className="answerCardTop">
            <span className="answerIndex">{String(index + 1).padStart(2, "0")}</span>
            <span className={`answerStatus ${answer.status || "missing"}`}>{answer.status || "missing"}</span>
          </div>
          <h4 className="answerQuestion">{answer.question || "Question"}</h4>
          <p className="answerText">{answer.answer || "No answer returned."}</p>
          <div className="answerFooter">
            <span>Confidence {answer.confidence ?? 0}</span>
            {Array.isArray(answer.evidence_fields) && answer.evidence_fields.length > 0 ? (
              <span>{answer.evidence_fields.join(" • ")}</span>
            ) : (
              <span>No evidence fields</span>
            )}
          </div>
        </article>
      ))}
    </div>
  );
}

function EducationTrendChart({ rows }) {
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
    return (
      <div className="chartEmpty">
        Not enough normalized education scores to plot a trend yet.
      </div>
    );
  }

  const width = 920;
  const height = 280;
  const padding = { top: 24, right: 24, bottom: 48, left: 56 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const sorted = [...points].sort((a, b) => a.year - b.year);
  const rawValues = sorted.map((point) => point.rawValue).filter((value) => Number.isFinite(value));
  const hasRawSeries = rawValues.length >= 2;
  const rawMin = hasRawSeries ? Math.min(...rawValues) : 0;
  const rawMax = hasRawSeries ? Math.max(...rawValues) : 100;

  const xFor = (index) =>
    padding.left + (sorted.length === 1 ? plotWidth / 2 : (plotWidth * index) / (sorted.length - 1));
  const yFor = (value) => padding.top + plotHeight - (Math.max(0, Math.min(100, value)) / 100) * plotHeight;
  const rawScaledYFor = (value) => {
    if (!Number.isFinite(value)) return null;
    if (rawMax === rawMin) {
      return yFor(50);
    }
    const scaled = ((value - rawMin) / (rawMax - rawMin)) * 100;
    return yFor(scaled);
  };

  const normalizedPath = sorted
    .map((point, index) => `${index === 0 ? "M" : "L"} ${xFor(index)} ${yFor(point.value)}`)
    .join(" ");

  const rawPath = sorted
    .map((point, index) => {
      const y = rawScaledYFor(point.rawValue);
      return Number.isFinite(y) ? `${index === 0 ? "M" : "L"} ${xFor(index)} ${y}` : null;
    })
    .filter(Boolean)
    .join(" ");

  function showPoint(point, index) {
    const x = xFor(index);
    const normalizedY = yFor(point.value);
    const rawY = rawScaledYFor(point.rawValue);
    setHovered({
      ...point,
      index,
      x,
      normalizedY,
      rawY,
      rawMin,
      rawMax,
      hasRawSeries,
    });
  }

  return (
    <div className="chartShell">
      <div className="chartHeader">
        <div>
          <p className="eyebrow">Trend</p>
          <h4>Normalized Education Scores</h4>
        </div>
        <div className="chartLegend">
          <span className="legendItem"><span className="legendLine normalized" />Normalized</span>
          <span className="legendItem"><span className="legendLine raw" />Raw trend</span>
        </div>
      </div>
      <div className="chartStage">
        <svg className="trendChart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Education score trend">
          <defs>
            <linearGradient id="trendFill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="rgba(6, 182, 212, 0.28)" />
              <stop offset="100%" stopColor="rgba(6, 182, 212, 0.02)" />
            </linearGradient>
          </defs>

          {[0, 25, 50, 75, 100].map((tick) => {
            const y = yFor(tick);
            return (
              <g key={`tick-${tick}`}>
                <line x1={padding.left} x2={width - padding.right} y1={y} y2={y} className="chartGridLine" />
                <text x={padding.left - 10} y={y + 4} textAnchor="end" className="chartAxisLabel">
                  {tick}
                </text>
              </g>
            );
          })}

          <path
            d={`${normalizedPath} L ${xFor(sorted.length - 1)} ${height - padding.bottom} L ${xFor(0)} ${height - padding.bottom} Z`}
            className="trendArea"
            fill="url(#trendFill)"
          />
          <path d={normalizedPath} className="trendLine normalized" />
          {hasRawSeries && <path d={rawPath} className="trendLine raw" />}

          {sorted.map((point, index) => {
            const x = xFor(index);
            const y = yFor(point.value);
            const rawY = rawScaledYFor(point.rawValue);
            return (
              <g
                key={`${point.year}-${index}`}
                onMouseEnter={() => showPoint(point, index)}
                onMouseLeave={() => setHovered(null)}
              >
                <circle cx={x} cy={y} r="6" className="trendPoint normalized" />
                {Number.isFinite(rawY) && <circle cx={x} cy={rawY} r="5" className="trendPoint raw" />}
                <circle cx={x} cy={y} r="14" className="trendHitArea" />
                <text x={x} y={height - padding.bottom + 18} textAnchor="middle" className="chartAxisLabel">
                  {point.year}
                </text>
              </g>
            );
          })}
        </svg>

        {hovered && (
          <div className="chartTooltip">
            <div className="chartTooltipTitle">
              {hovered.year} · {hovered.label}
            </div>
            <div className="chartTooltipSub">{hovered.institution || "Institution not listed"}</div>
            <div className="chartTooltipRows">
              <div><span>Normalized</span><strong>{hovered.value}</strong></div>
              <div><span>Raw</span><strong>{hovered.rawLabel}</strong></div>
              {hovered.hasRawSeries && Number.isFinite(hovered.rawValue) && (
                <div><span>Raw range</span><strong>{hovered.rawMin} to {hovered.rawMax}</strong></div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const NAV_ITEMS = [
  { id: "upload", label: "Upload and parse CVs", description: "Import PDFs and create parsed candidate records." },
  { id: "documents", label: "Previously parsed CVs", description: "Browse parsed profiles and switch the active CV." },
  { id: "analysis", label: "Analysis and scores", description: "Review education, skills, research, and more." },
];

const ANALYSIS_MODULES = [
  { id: "education", label: "Education", description: "Academic progression and normalized score trend." },
  { id: "skills", label: "Skills", description: "Evidence-backed capability map and coverage." },
  { id: "experience", label: "Experience", description: "Career continuity and role progression." },
  { id: "research", label: "Research", description: "Publication verification and venue quality." },
  { id: "supervision", label: "Supervision", description: "Mentorship and advising history." },
  { id: "awards", label: "Awards", description: "Recognition timeline and issuers." },
  { id: "books_patents", label: "Books / Patents", description: "Merged books and patents profile." },
];

export default function App() {
  const [backendUrl, setBackendUrl] = useState("http://127.0.0.1:8000");
  const [forceReprocess, setForceReprocess] = useState(false);
  const [files, setFiles] = useState([]);
  const [uploadResult, setUploadResult] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [docs, setDocs] = useState([]);
  const [selectedDocId, setSelectedDocId] = useState("");
  const [selectedDocDetail, setSelectedDocDetail] = useState(null);
  const [educationFacts, setEducationFacts] = useState(null);
  const [educationAnalysis, setEducationAnalysis] = useState(null);
  const [skillsFacts, setSkillsFacts] = useState(null);
  const [skillsAnalysis, setSkillsAnalysis] = useState(null);
  const [experienceFacts, setExperienceFacts] = useState(null);
  const [experienceAnalysis, setExperienceAnalysis] = useState(null);
  const [researchFacts, setResearchFacts] = useState(null);
  const [researchAnalysis, setResearchAnalysis] = useState(null);
  const [awardsData, setAwardsData] = useState(null);
  const [booksPatentsFacts, setBooksPatentsFacts] = useState(null);
  const [booksPatentsAnalysis, setBooksPatentsAnalysis] = useState(null);
  const [supervisionFacts, setSupervisionFacts] = useState(null);
  const [supervisionAnalysis, setSupervisionAnalysis] = useState(null);
  const [activeSection, setActiveSection] = useState("upload");
  const [activeModule, setActiveModule] = useState("education");
  const [regen, setRegen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState("");
  const [error, setError] = useState("");
  const [showRaw, setShowRaw] = useState(false);
  const fileInputRef = useRef(null);

  const client = useMemo(() => api(backendUrl), [backendUrl]);
  const researchVerificationRows = researchFacts?.facts?.publication_verifications || [];
  const researchCacheHitCount = researchVerificationRows.filter((row) => row.verification?.from_cache).length;
  const researchIssueCount = researchVerificationRows.reduce(
    (total, row) => total + (row.verification?.issues || []).length,
    0
  );
  const researchUnverifiedCount = researchVerificationRows.filter(
    (row) => row.verification?.verification_status === "unverified"
  ).length;
  const activeModuleMeta = ANALYSIS_MODULES.find((module) => module.id === activeModule) || ANALYSIS_MODULES[0];
  const activeNavMeta = NAV_ITEMS.find((item) => item.id === activeSection) || NAV_ITEMS[0];
  const selectedCandidateName =
    selectedDocDetail?.candidate_name || selectedDocDetail?.parsed_payload?.name?.value || "No CV selected";

  function handleFileSelection(event) {
    const nextFiles = Array.from(event.target.files || []);
    setFiles(nextFiles);
    setUploadResult(null);
    setUploadProgress(0);
  }

  function openFilePicker() {
    fileInputRef.current?.click();
  }

  function removeSelectedFile(index) {
    setFiles((current) => current.filter((_, i) => i !== index));
    setUploadResult(null);
  }

  function clearSelectedFiles() {
    setFiles([]);
    setUploadResult(null);
    setUploadProgress(0);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  useEffect(() => {
    handleRefreshDocs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleUpload() {
    if (!files.length) return;
    setLoadingMessage("Uploading and parsing CVs...");
    setLoading(true);
    setError("");
    setUploadProgress(0);
    try {
      const data = await uploadCVs(client, files, forceReprocess, (progressEvent) => {
        if (progressEvent.total) {
          setUploadProgress(Math.round((progressEvent.loaded * 100) / progressEvent.total));
        }
      });
      setUploadResult(data);
      setUploadProgress(100);
      await handleRefreshDocs();
    } catch (err) {
      setError(err?.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleRefreshDocs() {
    setLoadingMessage("Refreshing documents...");
    setLoading(true);
    setError("");
    try {
      const data = await listDocuments(client);
      setDocs(data.documents || []);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleLoadDoc(documentId) {
    setLoadingMessage("Loading document details...");
    setLoading(true);
    setError("");
    try {
      const data = await getDocument(client, documentId);
      setSelectedDocId(documentId);
      setSelectedDocDetail(data);
      setEducationFacts(null);
      setEducationAnalysis(null);
      setSkillsFacts(null);
      setSkillsAnalysis(null);
      setExperienceFacts(null);
      setExperienceAnalysis(null);
      setResearchFacts(null);
      setResearchAnalysis(null);
      setAwardsData(null);
      setBooksPatentsFacts(null);
      setBooksPatentsAnalysis(null);
      setSupervisionFacts(null);
      setSupervisionAnalysis(null);
      setActiveModule("education");
      setActiveSection("documents");
    } catch (err) {
      setError(err?.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  }

  function handleDocumentSelection(documentId) {
    setSelectedDocId(documentId);
    setEducationFacts(null);
    setEducationAnalysis(null);
    setSkillsFacts(null);
    setSkillsAnalysis(null);
    setExperienceFacts(null);
    setExperienceAnalysis(null);
    setResearchFacts(null);
    setResearchAnalysis(null);
    setAwardsData(null);
    setBooksPatentsFacts(null);
    setBooksPatentsAnalysis(null);
    setSupervisionFacts(null);
    setSupervisionAnalysis(null);
    setActiveSection("analysis");
  }

  async function handleLoadSkillsFacts() {
    if (!selectedDocId) return;
    setLoadingMessage("Loading skills facts...");
    setLoading(true);
    setError("");
    try {
      const data = await getSkillsFacts(client, selectedDocId);
      setSkillsFacts(data);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleAnalyzeSkills() {
    if (!selectedDocId) return;
    setLoadingMessage("Running skills analysis...");
    setLoading(true);
    setError("");
    try {
      const data = await analyzeSkills(client, selectedDocId, regen);
      setSkillsAnalysis(data);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleLoadExperienceFacts() {
    if (!selectedDocId) return;
    setLoadingMessage("Loading experience facts...");
    setLoading(true);
    setError("");
    try {
      const data = await getExperienceFacts(client, selectedDocId);
      setExperienceFacts(data);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleAnalyzeExperience() {
    if (!selectedDocId) return;
    setLoadingMessage("Running experience analysis...");
    setLoading(true);
    setError("");
    try {
      const data = await analyzeExperience(client, selectedDocId, regen);
      setExperienceAnalysis(data);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleLoadResearchFacts() {
    if (!selectedDocId) return;
    setLoadingMessage("Loading research facts...");
    setLoading(true);
    setError("");
    try {
      const data = await getResearchFacts(client, selectedDocId);
      setResearchFacts(data);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleAnalyzeResearch() {
    if (!selectedDocId) return;
    setLoadingMessage("Running research analysis...");
    setLoading(true);
    setError("");
    try {
      const data = await analyzeResearch(client, selectedDocId, regen);
      setResearchAnalysis(data);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleRecheckUnverifiedResearch() {
    if (!selectedDocId) return;
    setLoadingMessage("Rechecking unverified papers...");
    setLoading(true);
    setError("");
    try {
      const data = await recheckUnverifiedResearch(client, selectedDocId);
      setResearchFacts(data);
      setResearchAnalysis(null);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleLoadAwards() {
    if (!selectedDocId) return;
    setLoadingMessage("Loading awards...");
    setLoading(true);
    setError("");
    try {
      const doc = selectedDocDetail?.document_id === selectedDocId ? selectedDocDetail : await getDocument(client, selectedDocId);
      if (!selectedDocDetail || selectedDocDetail.document_id !== selectedDocId) {
        setSelectedDocDetail(doc);
      }
      const awards = Array.isArray(doc.parsed_payload?.awards) ? doc.parsed_payload.awards : [];
      setAwardsData({
        document_id: doc.document_id,
        file_name: doc.file_name,
        awards,
      });
    } catch (err) {
      setError(err?.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleLoadBooksPatentsFacts() {
    if (!selectedDocId) return;
    setLoadingMessage("Loading books and patents facts...");
    setLoading(true);
    setError("");
    try {
      const data = await getBooksPatentsFacts(client, selectedDocId);
      setBooksPatentsFacts(data);
      setBooksPatentsAnalysis(null);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleAnalyzeBooksPatents() {
    if (!selectedDocId) return;
    setLoadingMessage("Running books and patents analysis...");
    setLoading(true);
    setError("");
    try {
      const data = await analyzeBooksPatents(client, selectedDocId, regen);
      setBooksPatentsAnalysis(data);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleLoadSupervisionFacts() {
    if (!selectedDocId) return;
    setLoadingMessage("Loading supervision facts...");
    setLoading(true);
    setError("");
    try {
      const data = await getSupervisionFacts(client, selectedDocId);
      setSupervisionFacts(data);
      setSupervisionAnalysis(null);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleAnalyzeSupervision() {
    if (!selectedDocId) return;
    setLoadingMessage("Running supervision analysis...");
    setLoading(true);
    setError("");
    try {
      const data = await analyzeSupervision(client, selectedDocId, regen);
      setSupervisionAnalysis(data);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleReprocess(documentId) {
    setLoading(true);
    setError("");
    try {
      await reprocessDocument(client, documentId);
      await handleLoadDoc(documentId);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleLoadEducationFacts() {
    if (!selectedDocId) return;
    setLoadingMessage("Loading education facts...");
    setLoading(true);
    setError("");
    try {
      const data = await getEducationFacts(client, selectedDocId);
      setEducationFacts(data);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleAnalyzeEducation() {
    if (!selectedDocId) return;
    setLoadingMessage("Running education analysis...");
    setLoading(true);
    setError("");
    try {
      const data = await analyzeEducation(client, selectedDocId, regen);
      setEducationAnalysis(data);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sidebarBrand">
          <h1 className="logo">
            <span>TALASH</span>
          </h1>
          <p className="sidebarTag">Executive candidate dossier</p>
        </div>

        <div className="sidebarCard">
          <label className="checkboxRow">
            <input
              type="checkbox"
              checked={forceReprocess}
              onChange={(e) => setForceReprocess(e.target.checked)}
            />
            Force reprocess duplicates
          </label>
        </div>

        <div className="sidebarCard navCard">
          <div className="sidebarCardLabel">Navigation</div>
          <div className="navGroup">
            {NAV_ITEMS.map((item) => (
              <button
                key={item.id}
                className={`navButton ${activeSection === item.id ? "active" : ""}`}
                onClick={() => setActiveSection(item.id)}
              >
                <span className="navButtonTop">
                  <NavIcon id={item.id} />
                  <span className="navButtonLabel">{item.label}</span>
                </span>
                <span className="navButtonDesc">{item.description}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="sidebarCard sidebarSummary">
          <div className="sidebarCardLabel">Current dossier</div>
          <div className="selectedDocBadge">{selectedDocDetail?.status || "No CV selected"}</div>
          <div className="sidebarSummaryName">{selectedCandidateName}</div>
          <div className="sidebarSummaryTitle">{selectedDocDetail?.file_name || "No document loaded"}</div>
          <div className="sidebarSummaryMeta">{selectedDocDetail?.status || "Awaiting selection"}</div>
          <div className="sidebarSummaryGrid">
            <div>
              <span>Documents</span>
              <strong>{docs.length}</strong>
            </div>
            <div>
              <span>Current view</span>
              <strong>{activeModuleMeta.label}</strong>
            </div>
          </div>
        </div>
      </aside>

      <main className="content">
        <section className="heroPanel">
          <div className="heroCopy">
            <h1 className="heroTitle">TALASH WORKSPACE</h1>
            <p className="heroSubtitle">Automated CV Analysis</p>
          </div>
        </section>

        <section className="selectedDocBanner">
          <div>
            <p className="eyebrow">Selected CV</p>
            <h3 className="selectedCvName">
              <CvIcon />
              <span>{selectedCandidateName}</span>
            </h3>
          </div>
          <div className="selectedDocActions">
            <button className="btn secondary" onClick={() => setActiveSection("documents")}>
              {selectedDocDetail ? "Change CV" : "Select CV"}
            </button>
          </div>
        </section>

        {activeSection === "upload" && (
          <section className="card">
            <div className="sectionBanner">
              <div>
                <h2>Upload and parse CVs</h2>
              </div>
            </div>
            <div className="uploadControls">
              <button className="btn secondary" type="button" onClick={openFilePicker}>
                Choose Files
              </button>
              <span className="fileCountBadge">{files.length} selected</span>
              <input
                ref={fileInputRef}
                className="fileInputHidden"
                type="file"
                accept="application/pdf"
                multiple
                onChange={handleFileSelection}
              />
            </div>
            {files.length > 0 && (
              <div className="fileTray">
                {files.map((file, index) => (
                  <div className="fileChip" key={`${file.name}-${index}`}>
                    <FileIcon />
                    <span className="fileChipName">{file.name}</span>
                    <button className="fileChipRemove" type="button" onClick={() => removeSelectedFile(index)}>
                      Discard
                    </button>
                  </div>
                ))}
                <button className="btn secondary tiny clearAllButton" type="button" onClick={clearSelectedFiles}>
                  Clear All
                </button>
              </div>
            )}

            {loading && activeSection === "upload" && (
              <div className="uploadProgressWrap" aria-label="Upload progress">
                <div className="uploadProgressHeader">
                  <span>{loadingMessage || "Uploading..."}</span>
                  <strong>{uploadProgress}%</strong>
                </div>
                <div className="uploadProgressBar">
                  <div className="uploadProgressFill" style={{ width: `${uploadProgress}%` }} />
                </div>
              </div>
            )}

            <button className="btn" onClick={handleUpload} disabled={loading || files.length === 0}>
              {loading ? "Processing..." : "Process CVs"}
            </button>
            {uploadResult && (
              <>
                <div className="tilesRow">
                  <SummaryTile
                    label="Total Files"
                    value={(uploadResult.results || []).length}
                  />
                  <SummaryTile
                    label="Success"
                    value={(uploadResult.results || []).filter((x) => x.status === "success").length}
                  />
                  <SummaryTile
                    label="Failed"
                    value={(uploadResult.results || []).filter((x) => x.status === "failed").length}
                  />
                  <SummaryTile
                    label="Skipped"
                    value={(uploadResult.results || []).filter((x) => x.status === "skipped").length}
                  />
                </div>

                <table className="dataTable">
                  <thead>
                    <tr>
                      <th>File</th>
                      <th>Status</th>
                      <th>Document ID</th>
                      <th>Notes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(uploadResult.results || []).map((r, idx) => (
                      <tr key={`${r.file}-${idx}`}>
                        <td>{r.file}</td>
                        <td>
                          <span className={`badge ${r.status}`}>{r.status}</span>
                        </td>
                        <td>{r.document_id || "-"}</td>
                        <td>{r.error || r.reason || "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}
          </section>
        )}

        {activeSection === "documents" && (
          <section className="card">
            <div className="sectionBanner">
              <div>
                <h2>Previously parsed CVs</h2>
                <p className="sectionMeta">Total loaded CVs: {docs.length}</p>
              </div>
            </div>

            <div className="docTableWrap">
              <table className="dataTable">
                <thead>
                  <tr>
                    <th>File</th>
                    <th>Status</th>
                    <th>Document ID</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {docs.map((doc) => (
                    <tr key={doc.document_id} className={selectedDocId === doc.document_id ? "selectedRow" : ""}>
                      <td>
                        <button className="linkButton" onClick={() => handleLoadDoc(doc.document_id)}>
                          {doc.file_name}
                        </button>
                      </td>
                      <td>
                        <span className={`badge ${doc.status}`}>{doc.status}</span>
                      </td>
                      <td>{doc.document_id}</td>
                      <td>
                        <div className="docActions">
                          <button className="btn small" onClick={() => handleLoadDoc(doc.document_id)}>
                            Select
                          </button>
                          <button className="btn small secondary" onClick={() => handleReprocess(doc.document_id)}>
                            Reprocess
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {selectedDocDetail && (
              <>
                <div className="tilesRow">
                  <SummaryTile label="Candidate" value={selectedCandidateName} />
                  <SummaryTile label="Document ID" value={selectedDocDetail.document_id} />
                  <SummaryTile label="File" value={selectedDocDetail.file_name} />
                  <SummaryTile label="Status" value={selectedDocDetail.status} />
                  <SummaryTile label="Jobs" value={(selectedDocDetail.jobs || []).length} />
                </div>
                <label className="checkboxRow compact">
                  <input type="checkbox" checked={showRaw} onChange={(e) => setShowRaw(e.target.checked)} />
                  Show raw parsed JSON
                </label>
                {showRaw && (
                  <pre className="jsonBlock">{prettyJson(selectedDocDetail.parsed_payload || {})}</pre>
                )}
              </>
            )}
          </section>
        )}

        {activeSection === "analysis" && (
          <section className="card">
            <div className="sectionBanner">
              <div>
                <h2>Analysis and scores</h2>
              </div>
            </div>

            <div className="moduleTabs" role="tablist" aria-label="Analysis Sections">
              {ANALYSIS_MODULES.map((module) => (
                <button
                  key={module.id}
                  className={`tabBtn ${activeModule === module.id ? "active" : ""}`}
                  onClick={() => setActiveModule(module.id)}
                  title={module.description}
                  aria-label={`${module.label}: ${module.description}`}
                >
                  <ModuleIcon id={module.id} />
                  {module.label}
                </button>
              ))}
            </div>

            <div className="moduleIntro">
              <p className="eyebrow">{activeModuleMeta.label}</p>
            </div>

            {activeModule === "education" ? (
            <>
              <div className="rowButtons">
                <button className="btn" onClick={handleLoadEducationFacts} disabled={loading || !selectedDocId}>
                  Load Facts
                </button>
                <button className="btn secondary" onClick={handleAnalyzeEducation} disabled={loading || !selectedDocId}>
                  Run Analysis
                </button>
              </div>

              {educationFacts && (
                <>
                  <h3>Education Facts</h3>
                  <div className="tilesRow">
                    <SummaryTile
                      label="Highest Degree"
                      value={educationFacts.facts?.highest_qualification?.degree_title || "missing"}
                    />
                    <SummaryTile
                      label="Institution"
                      value={educationFacts.facts?.highest_qualification?.institution || "missing"}
                    />
                    <SummaryTile
                      label="Records"
                      value={educationFacts.facts?.education_records_count || 0}
                    />
                    <SummaryTile
                      label="Normalized Scores"
                      value={educationFacts.facts?.score_summary?.normalized_scores_available || 0}
                    />
                  </div>

                  <EducationTrendChart rows={educationFacts.facts?.education_timeline || []} />

                  <h4>Timeline</h4>
                  <table className="dataTable">
                    <thead>
                      <tr>
                        <th>Level</th>
                        <th>Degree</th>
                        <th>Institution</th>
                        <th>End Year</th>
                        <th>Score</th>
                        <th>Normalized</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(educationFacts.facts?.education_timeline || []).map((row, i) => (
                        <tr key={`edu-row-${i}`}>
                          <td>{row.level}</td>
                          <td>{row.degree_title}</td>
                          <td>{row.institution}</td>
                          <td>{row.end_year}</td>
                          <td>{row.score_raw} ({row.score_type})</td>
                          <td>{row.score_normalized_100 ?? "-"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  <h4>Detected Gaps</h4>
                  <table className="dataTable">
                    <thead>
                      <tr>
                        <th>From</th>
                        <th>To</th>
                        <th>Gap (Years)</th>
                        <th>Class</th>
                        <th>Justified</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(educationFacts.facts?.gaps || []).length === 0 ? (
                        <tr>
                          <td colSpan={5}>No detectable gaps</td>
                        </tr>
                      ) : (
                        (educationFacts.facts?.gaps || []).map((g, i) => (
                          <tr key={`gap-${i}`}>
                            <td>{g.from_stage}</td>
                            <td>{g.to_stage}</td>
                            <td>{g.gap_years}</td>
                            <td>{g.classification}</td>
                            <td>{String(g.justified_by_experience)}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </>
              )}

              {educationAnalysis && (
                <>
                  <h3>Education Analysis</h3>
                  <div className="tilesRow">
                    <SummaryTile
                      label="Strength"
                      value={educationAnalysis.analysis?.overall_education_assessment?.strength || "missing"}
                    />
                    <SummaryTile
                      label="Confidence"
                      value={educationAnalysis.analysis?.overall_education_assessment?.confidence ?? 0}
                    />
                    <SummaryTile
                      label="Model"
                      value={educationAnalysis.analysis_model || "default"}
                    />
                    <SummaryTile
                      label="Cached"
                      value={String(educationAnalysis.cached)}
                    />
                  </div>

                  <p className="summaryText">
                    {educationAnalysis.analysis?.overall_education_assessment?.summary || "No summary returned."}
                  </p>

                  <AnswerCardGrid answers={educationAnalysis.analysis?.answers || []} prefix="edu-ans" />
                </>
              )}
            </>
            ) : activeModule === "skills" ? (
            <>
              <div className="rowButtons">
                <button className="btn" onClick={handleLoadSkillsFacts} disabled={loading || !selectedDocId}>
                  Load Facts
                </button>
                <button className="btn secondary" onClick={handleAnalyzeSkills} disabled={loading || !selectedDocId}>
                  Run Analysis
                </button>
              </div>

              {skillsFacts && (
                <>
                  <h3>Skills Facts</h3>
                  <div className="tilesRow">
                    <SummaryTile label="Skills" value={skillsFacts.facts?.skills_count || 0} />
                    <SummaryTile
                      label="Strongly Evidenced"
                      value={skillsFacts.facts?.evidence_summary?.strongly_evidenced || 0}
                    />
                    <SummaryTile
                      label="Partially Evidenced"
                      value={skillsFacts.facts?.evidence_summary?.partially_evidenced || 0}
                    />
                    <SummaryTile
                      label="Coverage"
                      value={skillsFacts.facts?.evidence_summary?.coverage_ratio || 0}
                    />
                  </div>

                  <h4>Skills Evidence Table</h4>
                  <table className="dataTable">
                    <thead>
                      <tr>
                        <th>Skill</th>
                        <th>Claim Status</th>
                        <th>Evidence Strength</th>
                        <th>Evidence Sources</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(skillsFacts.facts?.skills_table || []).map((s, i) => (
                        <tr key={`skill-row-${i}`}>
                          <td>{s.skill}</td>
                          <td>{s.claim_status}</td>
                          <td>{s.evidence_strength}</td>
                          <td>{(s.evidence_sources || []).join(", ") || "-"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  <h4>Potentially Overstated</h4>
                  <p className="summaryText">
                    {(skillsFacts.facts?.potentially_overstated || []).join(", ") || "None"}
                  </p>
                </>
              )}

              {skillsAnalysis && (
                <>
                  <h3>Skills Analysis</h3>
                  <div className="tilesRow">
                    <SummaryTile
                      label="Strength"
                      value={skillsAnalysis.analysis?.overall_skills_assessment?.strength || "missing"}
                    />
                    <SummaryTile
                      label="Confidence"
                      value={skillsAnalysis.analysis?.overall_skills_assessment?.confidence ?? 0}
                    />
                    <SummaryTile
                      label="Model"
                      value={skillsAnalysis.analysis_model || "default"}
                    />
                    <SummaryTile
                      label="Cached"
                      value={String(skillsAnalysis.cached)}
                    />
                  </div>

                  <p className="summaryText">
                    {skillsAnalysis.analysis?.overall_skills_assessment?.summary || "No summary returned."}
                  </p>

                  <AnswerCardGrid answers={skillsAnalysis.analysis?.answers || []} prefix="skills-ans" />
                </>
              )}
            </>
            ) : activeModule === "experience" ? (
            <>
              <div className="rowButtons">
                <button className="btn" onClick={handleLoadExperienceFacts} disabled={loading || !selectedDocId}>
                  Load Facts
                </button>
                <button className="btn secondary" onClick={handleAnalyzeExperience} disabled={loading || !selectedDocId}>
                  Run Analysis
                </button>
              </div>

              {experienceFacts && (
                <>
                  <h3>Experience Facts</h3>
                  <div className="tilesRow">
                    <SummaryTile label="Records" value={experienceFacts.facts?.experience_records_count || 0} />
                    <SummaryTile label="Job Overlaps" value={(experienceFacts.facts?.job_overlaps || []).length} />
                    <SummaryTile label="Edu-Job Overlaps" value={(experienceFacts.facts?.education_job_overlaps || []).length} />
                    <SummaryTile label="Professional Gaps" value={(experienceFacts.facts?.professional_gaps || []).length} />
                  </div>

                  <h4>Timeline</h4>
                  <table className="dataTable">
                    <thead>
                      <tr>
                        <th>Job Title</th>
                        <th>Organization</th>
                        <th>Start</th>
                        <th>End</th>
                        <th>Current</th>
                        <th>Duration (Months)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(experienceFacts.facts?.experience_timeline || []).map((r, i) => (
                        <tr key={`exp-row-${i}`}>
                          <td>{r.job_title}</td>
                          <td>{r.organization}</td>
                          <td>{r.start_date}</td>
                          <td>{r.end_date}</td>
                          <td>{r.is_current}</td>
                          <td>{r.duration_months ?? "-"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  <h4>Job Overlaps</h4>
                  <table className="dataTable">
                    <thead>
                      <tr>
                        <th>Job A</th>
                        <th>Job B</th>
                        <th>Overlap (Months)</th>
                        <th>Note</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(experienceFacts.facts?.job_overlaps || []).length === 0 ? (
                        <tr>
                          <td colSpan={4}>No job overlaps detected</td>
                        </tr>
                      ) : (
                        (experienceFacts.facts?.job_overlaps || []).map((o, i) => (
                          <tr key={`job-overlap-${i}`}>
                            <td>{o.job_a}</td>
                            <td>{o.job_b}</td>
                            <td>{o.overlap_months}</td>
                            <td>{o.note}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>

                  <h4>Professional Gaps</h4>
                  <table className="dataTable">
                    <thead>
                      <tr>
                        <th>After Job</th>
                        <th>Before Job</th>
                        <th>Gap (Months)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(experienceFacts.facts?.professional_gaps || []).length === 0 ? (
                        <tr>
                          <td colSpan={3}>No significant professional gaps detected</td>
                        </tr>
                      ) : (
                        (experienceFacts.facts?.professional_gaps || []).map((g, i) => (
                          <tr key={`gap-row-${i}`}>
                            <td>{g.after_job}</td>
                            <td>{g.before_job}</td>
                            <td>{g.gap_months}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </>
              )}

              {experienceAnalysis && (
                <>
                  <h3>Experience Analysis</h3>
                  <div className="tilesRow">
                    <SummaryTile
                      label="Strength"
                      value={experienceAnalysis.analysis?.overall_experience_assessment?.strength || "missing"}
                    />
                    <SummaryTile
                      label="Confidence"
                      value={experienceAnalysis.analysis?.overall_experience_assessment?.confidence ?? 0}
                    />
                    <SummaryTile label="Model" value={experienceAnalysis.analysis_model || "default"} />
                    <SummaryTile label="Cached" value={String(experienceAnalysis.cached)} />
                  </div>

                  <p className="summaryText">
                    {experienceAnalysis.analysis?.overall_experience_assessment?.summary || "No summary returned."}
                  </p>

                  <AnswerCardGrid answers={experienceAnalysis.analysis?.answers || []} prefix="exp-ans" />
                </>
              )}
            </>
            ) : activeModule === "research" ? (
            <>
              <div className="rowButtons">
                <button className="btn" onClick={handleLoadResearchFacts} disabled={loading || !selectedDocId}>
                  Load Facts
                </button>
                <button className="btn secondary" onClick={handleAnalyzeResearch} disabled={loading || !selectedDocId}>
                  Run Analysis
                </button>
                {researchFacts && researchUnverifiedCount > 0 ? (
                  <button className="btn secondary" onClick={handleRecheckUnverifiedResearch} disabled={loading || !selectedDocId}>
                    Recheck Unverified ({researchUnverifiedCount})
                  </button>
                ) : researchFacts ? (
                  <span className="summaryText">No unverified papers to recheck.</span>
                ) : null}
              </div>

              {researchFacts && (
                <>
                  <h3>Research Facts</h3>
                  <div className="tilesRow">
                    <SummaryTile label="Publications" value={researchFacts.facts?.publications_count || 0} />
                    <SummaryTile label="Cache Hits" value={researchCacheHitCount} />
                    <SummaryTile
                      label="Verified"
                      value={researchFacts.facts?.verification_summary?.verified || 0}
                    />
                    <SummaryTile
                      label="Partial"
                      value={researchFacts.facts?.verification_summary?.partial || 0}
                    />
                    <SummaryTile
                      label="Avg Confidence"
                      value={researchFacts.facts?.verification_summary?.average_confidence || 0}
                    />
                    <SummaryTile label="Issues" value={researchIssueCount} />
                  </div>

                  <h4>Publication Verifications</h4>
                  <table className="dataTable">
                    <thead>
                      <tr>
                        <th>Title</th>
                        <th>Type</th>
                        <th>Place</th>
                        <th>DOI</th>
                        <th>Status</th>
                        <th>Source</th>
                        <th>Confidence</th>
                        <th>Cache</th>
                        <th>Issues</th>
                        <th>Venue Rank</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(researchFacts.facts?.publication_verifications || []).map((row, i) => (
                        <tr key={`research-row-${i}`}>
                          <td>{row.claim?.title}</td>
                          <td>{row.verified_publication?.publication_type || "-"}</td>
                          <td>{row.verified_publication?.publication_place || "-"}</td>
                          <td>
                            {row.verified_publication?.doi_url ? (
                              <a href={row.verified_publication.doi_url} target="_blank" rel="noreferrer">
                                DOI link
                              </a>
                            ) : (
                              "-"
                            )}
                          </td>
                          <td>{row.verification?.verification_status}</td>
                          <td>{row.verification?.source_best || "-"}</td>
                          <td>{row.verification?.confidence ?? 0}</td>
                          <td>{String(Boolean(row.verification?.from_cache))}</td>
                          <td>{(row.verification?.issues || []).join(", ") || "-"}</td>
                          <td>{row.verification?.matched_metadata?.venue_rank || "-"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  <h4>Topic Variability</h4>
                  <p className="summaryText">
                    {(researchFacts.facts?.topic_variability?.top_topics || []).join(", ") || "No topics detected"}
                  </p>
                </>
              )}

              {researchAnalysis && (
                <>
                  <h3>Research Analysis</h3>
                  <div className="tilesRow">
                    <SummaryTile
                      label="Strength"
                      value={researchAnalysis.analysis?.overall_research_assessment?.strength || "missing"}
                    />
                    <SummaryTile
                      label="Confidence"
                      value={researchAnalysis.analysis?.overall_research_assessment?.confidence ?? 0}
                    />
                    <SummaryTile label="Model" value={researchAnalysis.analysis_model || "default"} />
                    <SummaryTile label="Cached" value={String(researchAnalysis.cached)} />
                  </div>

                  <p className="summaryText">
                    {researchAnalysis.analysis?.overall_research_assessment?.summary || "No summary returned."}
                  </p>

                  <AnswerCardGrid answers={researchAnalysis.analysis?.answers || []} prefix="research-ans" />
                </>
              )}
            </>
            ) : activeModule === "awards" ? (
            <>
              <div className="rowButtons">
                <button className="btn" onClick={handleLoadAwards} disabled={loading || !selectedDocId}>
                  Load Awards
                </button>
              </div>

              <h3>Awards Facts</h3>

              <p className="summaryText">
                A clean view of honors extracted from the CV, with emphasis on issuers and chronology.
              </p>

              {selectedDocDetail && (
                <div className="tilesRow">
                  <SummaryTile label="Candidate" value={selectedCandidateName} />
                  <SummaryTile label="File" value={selectedDocDetail.file_name || "-"} />
                  <SummaryTile label="Status" value={selectedDocDetail.status || "-"} />
                  <SummaryTile label="Awards" value={awardsData?.awards?.length || 0} />
                </div>
              )}

              {awardsData && (
                <>
                  <div className="tilesRow">
                    <SummaryTile
                      label="Unique Issuers"
                      value={new Set(awardsData.awards.map((a) => a?.issuer?.value).filter(Boolean)).size}
                    />
                    <SummaryTile
                      label="Latest Year"
                      value={Math.max(
                        0,
                        ...awardsData.awards
                          .map((a) => Number.parseInt(a?.year?.value, 10))
                          .filter((n) => Number.isFinite(n))
                      ) || "-"}
                    />
                    <SummaryTile label="File" value={awardsData.file_name || "-"} />
                  </div>

                  {awardsData.awards.length > 0 ? (
                    <div className="awardGrid">
                      {awardsData.awards.map((award, i) => (
                        <article className="awardCard" key={`award-${i}`}>
                          <div className="awardTopRow">
                            <span className="awardIndex">{String(i + 1).padStart(2, "0")}</span>
                            <span className="awardYear">{award?.year?.value || "Year unknown"}</span>
                          </div>
                          <h4 className="awardTitle">{award?.title?.value || "Untitled award"}</h4>
                          <p className="awardIssuer">{award?.issuer?.value || "Issuer not listed"}</p>
                          <div className="awardMeta">
                            <span className={`pill ${award?.title?.status || "missing"}`}>{award?.title?.status || "missing"}</span>
                            <span className={`pill ${award?.issuer?.status || "missing"}`}>{award?.issuer?.status || "missing"}</span>
                            <span className={`pill ${award?.year?.status || "missing"}`}>{award?.year?.status || "missing"}</span>
                          </div>
                          <p className="awardEvidence">
                            {award?.title?.evidence || award?.issuer?.evidence || award?.year?.evidence || "No evidence snippet available."}
                          </p>
                        </article>
                      ))}
                    </div>
                  ) : (
                    <div className="placeholderCard">
                      <h3>No awards found</h3>
                      <p>This CV does not currently expose an awards section in the parsed payload.</p>
                    </div>
                  )}
                </>
              )}
            </>
            ) : activeModule === "books_patents" ? (
            <>
              <div className="rowButtons">
                <button className="btn" onClick={handleLoadBooksPatentsFacts} disabled={loading || !selectedDocId}>
                  Load Facts
                </button>
                <button className="btn secondary" onClick={handleAnalyzeBooksPatents} disabled={loading || !selectedDocId}>
                  Run Analysis
                </button>
              </div>

              {booksPatentsFacts && (
                <>
                  <h3>Books / Patents Facts</h3>
                  <div className="tilesRow">
                    <SummaryTile label="Patents" value={booksPatentsFacts.facts?.patents_count || 0} />
                    <SummaryTile label="Books" value={booksPatentsFacts.facts?.books_count || 0} />
                    <SummaryTile label="Combined" value={booksPatentsFacts.facts?.combined_count || 0} />
                    <SummaryTile
                      label="Items Present"
                      value={String(Boolean(booksPatentsFacts.facts?.summary?.has_multiple_items))}
                    />
                  </div>

                  <h4>Combined Timeline</h4>
                  <table className="dataTable">
                    <thead>
                      <tr>
                        <th>Type</th>
                        <th>Title</th>
                        <th>Year</th>
                        <th>Metadata</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(booksPatentsFacts.facts?.combined_timeline || []).map((item, i) => (
                        <tr key={`bp-${i}`}>
                          <td>{item.kind}</td>
                          <td>{item.title}</td>
                          <td>{item.year || "-"}</td>
                          <td>
                            {item.kind === "patent"
                              ? `${item.patent_number || "-"} · ${item.country || "-"}`
                              : `${item.publisher || "-"} · ${item.isbn || "-"}`}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}

              {booksPatentsAnalysis && (
                <>
                  <h3>Books / Patents Analysis</h3>
                  <div className="tilesRow">
                    <SummaryTile
                      label="Strength"
                      value={booksPatentsAnalysis.analysis?.overall_books_patents_assessment?.strength || "missing"}
                    />
                    <SummaryTile
                      label="Confidence"
                      value={booksPatentsAnalysis.analysis?.overall_books_patents_assessment?.confidence ?? 0}
                    />
                    <SummaryTile label="Model" value={booksPatentsAnalysis.analysis_model || "default"} />
                    <SummaryTile label="Cached" value={String(booksPatentsAnalysis.cached)} />
                  </div>

                  <p className="summaryText">
                    {booksPatentsAnalysis.analysis?.overall_books_patents_assessment?.summary || "No summary returned."}
                  </p>

                  <AnswerCardGrid answers={booksPatentsAnalysis.analysis?.answers || []} prefix="bp-ans" />
                </>
              )}
            </>
            ) : activeModule === "supervision" ? (
            <>
              <div className="rowButtons">
                <button className="btn" onClick={handleLoadSupervisionFacts} disabled={loading || !selectedDocId}>
                  Load Facts
                </button>
                <button className="btn secondary" onClick={handleAnalyzeSupervision} disabled={loading || !selectedDocId}>
                  Run Analysis
                </button>
              </div>

              {supervisionFacts && (
                <>
                  <h3>Supervision Facts</h3>
                  <div className="tilesRow">
                    <SummaryTile label="Records" value={supervisionFacts.facts?.supervision_count || 0} />
                    <SummaryTile
                      label="Unique Students"
                      value={supervisionFacts.facts?.summary?.unique_students || 0}
                    />
                    <SummaryTile
                      label="Multiple Students"
                      value={String(Boolean(supervisionFacts.facts?.summary?.has_multiple_items))}
                    />
                    <SummaryTile
                      label="Roles"
                      value={Object.keys(supervisionFacts.facts?.role_distribution || {}).length}
                    />
                  </div>

                  <h4>Supervision Timeline</h4>
                  <table className="dataTable">
                    <thead>
                      <tr>
                        <th>Student</th>
                        <th>Level</th>
                        <th>Role</th>
                        <th>Graduation Year</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(supervisionFacts.facts?.supervision_timeline || []).map((item, i) => (
                        <tr key={`sup-${i}`}>
                          <td>{item.student_name}</td>
                          <td>{item.level}</td>
                          <td>{item.role}</td>
                          <td>{item.graduation_year}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}

              {supervisionAnalysis && (
                <>
                  <h3>Supervision Analysis</h3>
                  <div className="tilesRow">
                    <SummaryTile
                      label="Strength"
                      value={supervisionAnalysis.analysis?.overall_supervision_assessment?.strength || "missing"}
                    />
                    <SummaryTile
                      label="Confidence"
                      value={supervisionAnalysis.analysis?.overall_supervision_assessment?.confidence ?? 0}
                    />
                    <SummaryTile label="Model" value={supervisionAnalysis.analysis_model || "default"} />
                    <SummaryTile label="Cached" value={String(supervisionAnalysis.cached)} />
                  </div>

                  <p className="summaryText">
                    {supervisionAnalysis.analysis?.overall_supervision_assessment?.summary || "No summary returned."}
                  </p>

                  <AnswerCardGrid answers={supervisionAnalysis.analysis?.answers || []} prefix="sup-ans" />
                </>
              )}
            </>
            ) : (
            <div className="placeholderCard">
              <h3>{activeModule.charAt(0).toUpperCase() + activeModule.slice(1)} Module</h3>
              <p>
                This section is prepared as a placeholder and will be implemented in the next phase.
                For now, use the <strong>Education</strong> tab for full analysis.
              </p>
            </div>
            )}
          </section>
        )}

        {error && <div className="errorBox">{error}</div>}

        {loading && (
          <div className="loadingOverlay" role="status" aria-live="polite" aria-busy="true">
            <div className="loadingCard">
              <div className="spinner" />
              <div>
                <div className="loadingTitle">Processing</div>
                <div className="loadingText">{loadingMessage || "Working on your request..."}</div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
