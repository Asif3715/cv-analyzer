export const NAV_ITEMS = [
  { id: "upload", label: "Upload", description: "Import and parse CV PDFs" },
  { id: "documents", label: "Candidates", description: "Browse parsed profiles" },
  { id: "analysis", label: "Analysis", description: "Review scores and insights" },
];

export const ANALYSIS_MODULES = [
  { id: "education", label: "Education", description: "Academic progression and score trends" },
  { id: "skills", label: "Skills", description: "Evidence-backed capability assessment" },
  { id: "experience", label: "Experience", description: "Career continuity and role history" },
  { id: "research", label: "Research", description: "Publication verification and quality" },
  { id: "supervision", label: "Supervision", description: "Mentorship and advising record" },
  { id: "awards", label: "Awards", description: "Honors and recognition timeline" },
  { id: "books_patents", label: "Books & Patents", description: "Publications and IP portfolio" },
];

export const WORKFLOW_STEPS = [
  { id: "upload", label: "Upload CVs", section: "upload" },
  { id: "select", label: "Select Candidate", section: "documents" },
  { id: "analyze", label: "Run Analysis", section: "analysis" },
];
