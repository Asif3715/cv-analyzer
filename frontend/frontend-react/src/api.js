import axios from "axios";

export function api(baseURL) {
  return axios.create({
    baseURL,
    timeout: 300000
  });
}

export async function uploadCVs(client, files, forceReprocess, onUploadProgress) {
  const formData = new FormData();
  files.forEach((f) => formData.append("files", f));
  formData.append("force_reprocess", String(forceReprocess));
  const { data } = await client.post("/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress,
  });
  return data;
}

export async function listDocuments(client) {
  const { data } = await client.get("/documents");
  return data;
}

export async function getDocument(client, documentId) {
  const { data } = await client.get(`/documents/${documentId}`);
  return data;
}

export async function reprocessDocument(client, documentId) {
  const { data } = await client.post(`/documents/${documentId}/reprocess`);
  return data;
}

export async function getEducationFacts(client, documentId) {
  const { data } = await client.get(`/documents/${documentId}/education/facts`);
  return data;
}

export async function analyzeEducation(client, documentId, regenerate) {
  const formData = new FormData();
  formData.append("regenerate", String(regenerate));
  const { data } = await client.post(`/documents/${documentId}/education/analyze`, formData);
  return data;
}

export async function getSkillsFacts(client, documentId) {
  const { data } = await client.get(`/documents/${documentId}/skills/facts`);
  return data;
}

export async function analyzeSkills(client, documentId, regenerate) {
  const formData = new FormData();
  formData.append("regenerate", String(regenerate));
  const { data } = await client.post(`/documents/${documentId}/skills/analyze`, formData);
  return data;
}

export async function getExperienceFacts(client, documentId) {
  const { data } = await client.get(`/documents/${documentId}/experience/facts`);
  return data;
}

export async function analyzeExperience(client, documentId, regenerate) {
  const formData = new FormData();
  formData.append("regenerate", String(regenerate));
  const { data } = await client.post(`/documents/${documentId}/experience/analyze`, formData);
  return data;
}

export async function getResearchFacts(client, documentId) {
  const { data } = await client.get(`/documents/${documentId}/research/facts`);
  return data;
}

export async function analyzeResearch(client, documentId, regenerate) {
  const formData = new FormData();
  formData.append("regenerate", String(regenerate));
  const { data } = await client.post(`/documents/${documentId}/research/analyze`, formData);
  return data;
}

export async function recheckUnverifiedResearch(client, documentId) {
  const { data } = await client.post(`/documents/${documentId}/research/recheck-unverified`);
  return data;
}

export async function getBooksPatentsFacts(client, documentId) {
  const { data } = await client.get(`/documents/${documentId}/books-patents/facts`);
  return data;
}

export async function analyzeBooksPatents(client, documentId, regenerate) {
  const formData = new FormData();
  formData.append("regenerate", String(regenerate));
  const { data } = await client.post(`/documents/${documentId}/books-patents/analyze`, formData);
  return data;
}

export async function getBooksPatents(client, documentId) {
  const { data } = await client.get(`/documents/${documentId}/books-patents`);
  return data;
}

export async function getSupervisionFacts(client, documentId) {
  const { data } = await client.get(`/documents/${documentId}/supervision/facts`);
  return data;
}

export async function analyzeSupervision(client, documentId, regenerate) {
  const formData = new FormData();
  formData.append("regenerate", String(regenerate));
  const { data } = await client.post(`/documents/${documentId}/supervision/analyze`, formData);
  return data;
}

export async function getSupervision(client, documentId) {
  const { data } = await client.get(`/documents/${documentId}/supervision`);
  return data;
}
