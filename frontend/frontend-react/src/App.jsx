import { useEffect, useMemo, useRef, useState } from "react";
import {
  analyzeBooksPatents,
  analyzeExperience,
  analyzeResearch,
  analyzeSkills,
  analyzeEducation,
  api,
  getBooksPatentsFacts,
  getDocument,
  getEducationFacts,
  getExperienceFacts,
  getSupervisionFacts,
  analyzeSupervision,
  getResearchFacts,
  getSkillsFacts,
  listDocuments,
  reprocessDocument,
  recheckUnverifiedResearch,
  uploadCVs,
} from "./api";
import { ANALYSIS_MODULES, NAV_ITEMS } from "./constants";
import {
  AnswerCardGrid,
  AssessmentHero,
  AnalysisToolbar,
  DataTable,
  EducationTrendChart,
  EmptyState,
  FileIcon,
  ModuleRail,
  PageHeader,
  Section,
  Sidebar,
  SummaryTile,
} from "./components";

function prettyJson(value) {
  return JSON.stringify(value, null, 2);
}

export default function App() {
  const [backendUrl, setBackendUrl] = useState(import.meta.env.VITE_API_URL || "http://127.0.0.1:8000");
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
  const [isDragging, setIsDragging] = useState(false);
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
  const selectedCandidateName =
    selectedDocDetail?.candidate_name || selectedDocDetail?.parsed_payload?.name?.value || "No candidate selected";
  function addFiles(nextFiles) {
    const pdfs = nextFiles.filter((f) => f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf"));
    if (pdfs.length === 0) return;
    setFiles((current) => [...current, ...pdfs]);
    setUploadResult(null);
    setUploadProgress(0);
  }

  function handleFileSelection(event) {
    addFiles(Array.from(event.target.files || []));
  }

  function handleDrop(event) {
    event.preventDefault();
    setIsDragging(false);
    addFiles(Array.from(event.dataTransfer.files || []));
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
      setActiveSection("analysis");
    } catch (err) {
      setError(err?.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
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

  useEffect(() => {
    if (activeSection !== "analysis" || !selectedDocId) return;
    if (activeModule === "education" && !educationFacts) handleLoadEducationFacts();
    else if (activeModule === "skills" && !skillsFacts) handleLoadSkillsFacts();
    else if (activeModule === "experience" && !experienceFacts) handleLoadExperienceFacts();
    else if (activeModule === "research" && !researchFacts) handleLoadResearchFacts();
    else if (activeModule === "supervision" && !supervisionFacts) handleLoadSupervisionFacts();
    else if (activeModule === "awards" && !awardsData) handleLoadAwards();
    else if (activeModule === "books_patents" && !booksPatentsFacts) handleLoadBooksPatentsFacts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeModule, activeSection, selectedDocId]);

  const sectionLabels = { upload: "Upload", documents: "Candidates", analysis: "Analysis" };
  const breadcrumbModule = activeSection === "analysis" && selectedDocId ? activeModuleMeta.label : null;

  return (
    <div className="app">
      <Sidebar
        brand={(
          <div className="brandMark">
            <div className="brandIcon">T</div>
            <div className="brandText">
              <h1>Talash</h1>
              <p>CV intelligence</p>
            </div>
          </div>
        )}
        navItems={NAV_ITEMS}
        activeSection={activeSection}
        onNavigate={setActiveSection}
        candidates={docs}
        selectedDocId={selectedDocId}
        onSelectCandidate={(id) => {
          handleLoadDoc(id);
          setActiveSection("analysis");
        }}
        activeCandidate={
          selectedDocDetail
            ? { name: selectedCandidateName, file: selectedDocDetail.file_name }
            : null
        }
      />

      <div className="main">
        <header className="topbar">
          <div className="breadcrumb">
            <span>{sectionLabels[activeSection]}</span>
            {breadcrumbModule && (
              <>
                <span className="breadcrumbSep">/</span>
                <strong>{breadcrumbModule}</strong>
              </>
            )}
          </div>
          <div className="topbarActions">
            {activeSection === "documents" && docs.length > 0 && (
              <button className="btn btnGhost btnSm" type="button" onClick={handleRefreshDocs} disabled={loading}>
                Refresh
              </button>
            )}
            {!selectedDocId && docs.length > 0 && (
              <button className="btn btnSm" type="button" onClick={() => setActiveSection("documents")}>
                Browse candidates
              </button>
            )}
          </div>
        </header>

        <div className="content">
          <div className="contentInner">
          {error && (
            <div className="errorBanner" role="alert">
              <span>{error}</span>
              <button className="errorDismiss" onClick={() => setError("")} aria-label="Dismiss">×</button>
            </div>
          )}

          {activeSection === "upload" && (
            <>
              <PageHeader
                title="Upload CVs"
                description="Import PDF resumes. We extract structured profiles you can analyze module by module."
              />

              <div className="panel">
                <div
                  className={`dropzone ${isDragging ? "dragging" : ""}`}
                  onClick={openFilePicker}
                  onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={handleDrop}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => e.key === "Enter" && openFilePicker()}
                >
                  <svg className="dropzoneIcon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M12 16V6m0 0l-4 4m4-4l4 4M5 18h14" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  <p className="dropzoneTitle">Drop PDF files here</p>
                  <p className="dropzoneHint">or click to browse · multiple files supported</p>
                  <button className="btn btnGhost btnSm" type="button" onClick={(e) => { e.stopPropagation(); openFilePicker(); }}>
                    Choose files
                  </button>
                  <input
                    ref={fileInputRef}
                    className="fileInputHidden"
                    type="file"
                    accept="application/pdf"
                    multiple
                    onChange={handleFileSelection}
                  />
                </div>

                <label className="toggle" style={{ marginTop: 16 }}>
                  <input type="checkbox" checked={forceReprocess} onChange={(e) => setForceReprocess(e.target.checked)} />
                  Reprocess duplicate files
                </label>

                {files.length > 0 && (
                  <div className="fileList">
                    {files.map((file, index) => (
                      <div className="fileRow" key={`${file.name}-${index}`}>
                        <FileIcon />
                        <span className="fileRowName">{file.name}</span>
                        <button className="btnIcon" type="button" onClick={() => removeSelectedFile(index)} aria-label="Remove file">×</button>
                      </div>
                    ))}
                  </div>
                )}

                {loading && activeSection === "upload" && (
                  <div className="uploadProgress">
                    <div className="uploadProgressTop">
                      <span>{loadingMessage || "Uploading…"}</span>
                      <strong>{uploadProgress}%</strong>
                    </div>
                    <div className="uploadProgressBar">
                      <div className="uploadProgressFill" style={{ width: `${uploadProgress}%` }} />
                    </div>
                  </div>
                )}

                <div className="btnRow" style={{ marginTop: 16 }}>
                  <button className="btn" onClick={handleUpload} disabled={loading || files.length === 0}>
                    {loading ? "Processing…" : "Parse CVs"}
                  </button>
                  {files.length > 0 && (
                    <button className="btn btnGhost" type="button" onClick={clearSelectedFiles}>Clear all</button>
                  )}
                </div>

                {uploadResult && (
                  <>
                    <div className="sectionDivider" />
                    <div className="statsGrid">
                      <SummaryTile label="Total" value={(uploadResult.results || []).length} />
                      <SummaryTile label="Success" value={(uploadResult.results || []).filter((x) => x.status === "success").length} />
                      <SummaryTile label="Failed" value={(uploadResult.results || []).filter((x) => x.status === "failed").length} />
                      <SummaryTile label="Skipped" value={(uploadResult.results || []).filter((x) => x.status === "skipped").length} />
                    </div>
                    <div className="tableWrap">
                      <table className="dataTable">
                        <thead>
                          <tr><th>File</th><th>Status</th><th>Document ID</th><th>Notes</th></tr>
                        </thead>
                        <tbody>
                          {(uploadResult.results || []).map((r, idx) => (
                            <tr key={`${r.file}-${idx}`}>
                              <td>{r.file}</td>
                              <td><span className={`badge ${r.status}`}>{r.status}</span></td>
                              <td>{r.document_id || "—"}</td>
                              <td>{r.error || r.reason || "—"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <div className="btnRow" style={{ marginTop: 16 }}>
                      <button className="btn btnGhost btnSm" onClick={() => setActiveSection("documents")}>View candidates →</button>
                    </div>
                  </>
                )}
              </div>
            </>
          )}

          {activeSection === "documents" && (
            <>
              <PageHeader
                title="Candidates"
                description={`${docs.length} parsed CV${docs.length !== 1 ? "s" : ""} in your library. Select one to open the analysis workspace.`}
              />

              {docs.length === 0 ? (
                <EmptyState
                  title="No candidates yet"
                  description="Upload PDF resumes to get started."
                  action={<button className="btn btnSm" onClick={() => setActiveSection("upload")}>Upload CVs</button>}
                />
              ) : (
                <>
                  <div className="candidateGrid">
                    {docs.map((doc) => (
                      <button
                        key={doc.document_id}
                        className={`candidateCard ${selectedDocId === doc.document_id ? "selected" : ""}`}
                        onClick={() => handleLoadDoc(doc.document_id)}
                      >
                        <div className="candidateCardTop">
                          <span className="candidateCardName">{doc.file_name}</span>
                          <span className={`badge badgeSm ${doc.status}`}>{doc.status}</span>
                        </div>
                        <span className="candidateCardFile">ID {doc.document_id}</span>
                      </button>
                    ))}
                  </div>

                </>
              )}

              {selectedDocDetail && (
                <div className="panel">
                  <h2 className="panelTitle">Profile summary</h2>
                  <div className="statsGrid">
                    <SummaryTile label="Candidate" value={selectedCandidateName} />
                    <SummaryTile label="Document ID" value={selectedDocDetail.document_id} />
                    <SummaryTile label="File" value={selectedDocDetail.file_name} />
                    <SummaryTile label="Status" value={selectedDocDetail.status} />
                    <SummaryTile label="Jobs" value={(selectedDocDetail.jobs || []).length} />
                  </div>
                  <label className="toggle">
                    <input type="checkbox" checked={showRaw} onChange={(e) => setShowRaw(e.target.checked)} />
                    Show raw parsed JSON
                  </label>
                  {showRaw && <pre className="jsonBlock">{prettyJson(selectedDocDetail.parsed_payload || {})}</pre>}
                  <div className="btnRow" style={{ marginTop: 16 }}>
                    <button className="btn" onClick={() => setActiveSection("analysis")}>Continue to analysis →</button>
                  </div>
                </div>
              )}
            </>
          )}

          {activeSection === "analysis" && (
            <>
              {!selectedDocId ? (
                <EmptyState
                  title="Select a candidate"
                  description="Pick someone from the sidebar or Candidates page to unlock module analysis."
                  action={<button className="btn btnSm" type="button" onClick={() => setActiveSection("documents")}>Browse candidates</button>}
                />
              ) : (
                <div className="analysisShell">
                  <ModuleRail
                    modules={ANALYSIS_MODULES}
                    activeId={activeModule}
                    onSelect={setActiveModule}
                  />
                  <div className="analysisMain">
                    <div className="analysisModuleHead">
                      <h2>{activeModuleMeta.label}</h2>
                      <p>{activeModuleMeta.description}</p>
                    </div>

            {activeModule === "education" ? (
            <>
              <AnalysisToolbar
                onLoadFacts={handleLoadEducationFacts}
                onAnalyze={handleAnalyzeEducation}
                loading={loading}
                disabled={!selectedDocId}
                regen={regen}
                onRegenChange={setRegen}
              />

              {educationFacts && (
                <Section title="Structured facts" description="Deterministic extraction from the parsed CV — no AI interpretation.">
                  <div className="statsGrid">
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

                  <DataTable
                    columns={[
                      { key: "level", label: "Level" },
                      { key: "degree_title", label: "Degree" },
                      { key: "institution", label: "Institution" },
                      { key: "end_year", label: "End year" },
                      {
                        key: "score",
                        label: "Score",
                        render: (r) => `${r.score_raw} (${r.score_type})`,
                      },
                      {
                        key: "score_normalized_100",
                        label: "Normalized",
                        render: (r) => r.score_normalized_100 ?? "—",
                      },
                    ]}
                    rows={educationFacts.facts?.education_timeline || []}
                    emptyMessage="No education timeline entries"
                    getRowKey={(row, i) => `edu-${i}-${row.end_year}`}
                  />

                  <DataTable
                    columns={[
                      { key: "from_stage", label: "From" },
                      { key: "to_stage", label: "To" },
                      { key: "gap_years", label: "Gap (years)" },
                      { key: "classification", label: "Class" },
                      {
                        key: "justified",
                        label: "Justified",
                        render: (g) => String(g.justified_by_experience),
                      },
                    ]}
                    rows={educationFacts.facts?.gaps || []}
                    emptyMessage="No detectable education gaps"
                    getRowKey={(_, i) => `gap-${i}`}
                  />
                </Section>
              )}

              {educationAnalysis && (
                <Section title="AI insights" description="Model-generated assessment and question-level answers." variant="insights">
                  <AssessmentHero
                    strength={educationAnalysis.analysis?.overall_education_assessment?.strength}
                    confidence={educationAnalysis.analysis?.overall_education_assessment?.confidence ?? 0}
                    summary={educationAnalysis.analysis?.overall_education_assessment?.summary}
                    meta={[
                      { label: "Model", value: educationAnalysis.analysis_model || "default" },
                      { label: "Cached", value: String(educationAnalysis.cached) },
                    ]}
                  />
                  <AnswerCardGrid answers={educationAnalysis.analysis?.answers || []} prefix="edu-ans" />
                </Section>
              )}
            </>
            ) : activeModule === "skills" ? (
            <>
              <AnalysisToolbar
                onLoadFacts={handleLoadSkillsFacts}
                onAnalyze={handleAnalyzeSkills}
                loading={loading}
                disabled={!selectedDocId}
                regen={regen}
                onRegenChange={setRegen}
              />

              {skillsFacts && (
                <>
                  <h3>Skills Facts</h3>
                  <div className="statsGrid">
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
                <Section title="AI insights" description="Model-generated assessment and question-level answers." variant="insights">
                  <AssessmentHero
                    strength={skillsAnalysis.analysis?.overall_skills_assessment?.strength}
                    confidence={skillsAnalysis.analysis?.overall_skills_assessment?.confidence ?? 0}
                    summary={skillsAnalysis.analysis?.overall_skills_assessment?.summary}
                    meta={[
                      { label: "Model", value: skillsAnalysis.analysis_model || "default" },
                      { label: "Cached", value: String(skillsAnalysis.cached) },
                    ]}
                  />
                  <AnswerCardGrid answers={skillsAnalysis.analysis?.answers || []} prefix="skills-ans" />
                </Section>
              )}
            </>
            ) : activeModule === "experience" ? (
            <>
              <AnalysisToolbar
                onLoadFacts={handleLoadExperienceFacts}
                onAnalyze={handleAnalyzeExperience}
                loading={loading}
                disabled={!selectedDocId}
                regen={regen}
                onRegenChange={setRegen}
              />

              {experienceFacts && (
                <>
                  <h3>Experience Facts</h3>
                  <div className="statsGrid">
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
                <Section title="AI insights" description="Model-generated assessment and question-level answers." variant="insights">
                  <AssessmentHero
                    strength={experienceAnalysis.analysis?.overall_experience_assessment?.strength}
                    confidence={experienceAnalysis.analysis?.overall_experience_assessment?.confidence ?? 0}
                    summary={experienceAnalysis.analysis?.overall_experience_assessment?.summary}
                    meta={[
                      { label: "Model", value: experienceAnalysis.analysis_model || "default" },
                      { label: "Cached", value: String(experienceAnalysis.cached) },
                    ]}
                  />
                  <AnswerCardGrid answers={experienceAnalysis.analysis?.answers || []} prefix="exp-ans" />
                </Section>
              )}
            </>
            ) : activeModule === "research" ? (
            <>
              <AnalysisToolbar
                onLoadFacts={handleLoadResearchFacts}
                onAnalyze={handleAnalyzeResearch}
                loading={loading}
                disabled={!selectedDocId}
                regen={regen}
                onRegenChange={setRegen}
                extra={
                  researchFacts && researchUnverifiedCount > 0 ? (
                    <button className="btn btnGhost btnSm" type="button" onClick={handleRecheckUnverifiedResearch} disabled={loading || !selectedDocId}>
                      Recheck unverified ({researchUnverifiedCount})
                    </button>
                  ) : null
                }
              />

              {researchFacts && (
                <>
                  <h3>Research Facts</h3>
                  <div className="statsGrid">
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
                  <div className="tableWrap">
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
                  </div>

                  <h4>Topic Variability</h4>
                  <p className="summaryText">
                    {(researchFacts.facts?.topic_variability?.top_topics || []).join(", ") || "No topics detected"}
                  </p>
                </>
              )}

              {researchAnalysis && (
                <Section title="AI insights" description="Model-generated assessment and question-level answers." variant="insights">
                  <AssessmentHero
                    strength={researchAnalysis.analysis?.overall_research_assessment?.strength}
                    confidence={researchAnalysis.analysis?.overall_research_assessment?.confidence ?? 0}
                    summary={researchAnalysis.analysis?.overall_research_assessment?.summary}
                    meta={[
                      { label: "Model", value: researchAnalysis.analysis_model || "default" },
                      { label: "Cached", value: String(researchAnalysis.cached) },
                    ]}
                  />
                  <AnswerCardGrid answers={researchAnalysis.analysis?.answers || []} prefix="research-ans" />
                </Section>
              )}
            </>
            ) : activeModule === "awards" ? (
            <>
              <div className="analysisToolbar" style={{ marginBottom: 24 }}>
                <button className="btn btnSecondary" type="button" onClick={handleLoadAwards} disabled={loading || !selectedDocId}>
                  Load awards
                </button>
              </div>

              <Section title="Honors & awards" description="Honors extracted from the CV with issuer and chronology.">
              {selectedDocDetail && (
                <div className="statsGrid">
                  <SummaryTile label="Candidate" value={selectedCandidateName} />
                  <SummaryTile label="File" value={selectedDocDetail.file_name || "-"} />
                  <SummaryTile label="Status" value={selectedDocDetail.status || "-"} />
                  <SummaryTile label="Awards" value={awardsData?.awards?.length || 0} />
                </div>
              )}

              {awardsData && (
                <>
                  <div className="statsGrid">
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
              </Section>
            </>
            ) : activeModule === "books_patents" ? (
            <>
              <AnalysisToolbar
                onLoadFacts={handleLoadBooksPatentsFacts}
                onAnalyze={handleAnalyzeBooksPatents}
                loading={loading}
                disabled={!selectedDocId}
                regen={regen}
                onRegenChange={setRegen}
              />

              {booksPatentsFacts && (
                <>
                  <h3>Books / Patents Facts</h3>
                  <div className="statsGrid">
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
                <Section title="AI insights" description="Model-generated assessment and question-level answers." variant="insights">
                  <AssessmentHero
                    strength={booksPatentsAnalysis.analysis?.overall_books_patents_assessment?.strength}
                    confidence={booksPatentsAnalysis.analysis?.overall_books_patents_assessment?.confidence ?? 0}
                    summary={booksPatentsAnalysis.analysis?.overall_books_patents_assessment?.summary}
                    meta={[
                      { label: "Model", value: booksPatentsAnalysis.analysis_model || "default" },
                      { label: "Cached", value: String(booksPatentsAnalysis.cached) },
                    ]}
                  />
                  <AnswerCardGrid answers={booksPatentsAnalysis.analysis?.answers || []} prefix="bp-ans" />
                </Section>
              )}
            </>
            ) : activeModule === "supervision" ? (
            <>
              <AnalysisToolbar
                onLoadFacts={handleLoadSupervisionFacts}
                onAnalyze={handleAnalyzeSupervision}
                loading={loading}
                disabled={!selectedDocId}
                regen={regen}
                onRegenChange={setRegen}
              />

              {supervisionFacts && (
                <>
                  <h3>Supervision Facts</h3>
                  <div className="statsGrid">
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
                <Section title="AI insights" description="Model-generated assessment and question-level answers." variant="insights">
                  <AssessmentHero
                    strength={supervisionAnalysis.analysis?.overall_supervision_assessment?.strength}
                    confidence={supervisionAnalysis.analysis?.overall_supervision_assessment?.confidence ?? 0}
                    summary={supervisionAnalysis.analysis?.overall_supervision_assessment?.summary}
                    meta={[
                      { label: "Model", value: supervisionAnalysis.analysis_model || "default" },
                      { label: "Cached", value: String(supervisionAnalysis.cached) },
                    ]}
                  />
                  <AnswerCardGrid answers={supervisionAnalysis.analysis?.answers || []} prefix="sup-ans" />
                </Section>
              )}
            </>
            ) : (
            <div className="placeholderCard">
              <h3>{activeModuleMeta.label}</h3>
              <p>This module is not available yet.</p>
            </div>
            )}
                  </div>
                </div>
              )}
            </>
          )}
          </div>
        </div>

        {loading && (
          <>
            <div className="loadingBar"><div className="loadingBarFill" /></div>
            <div className="loadingToast" role="status" aria-live="polite">
              <div className="spinner" />
              <span>{loadingMessage || "Working…"}</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
