import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api",
  timeout: 30000,
});

const LONG_REQUEST_TIMEOUT = 180000;

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("docuverify_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const requestPath = error.config?.url || "";
    const isAuthRequest = requestPath.includes("/auth/login") || requestPath.includes("/auth/register");

    if (status === 401 && !isAuthRequest) {
      localStorage.removeItem("docuverify_token");
      window.dispatchEvent(new CustomEvent("docuverify:auth-expired"));
      if (!window.location.pathname.startsWith("/login")) window.location.assign("/login");
    }
    if (status === 403 && !window.location.pathname.startsWith("/access-denied")) {
      window.location.assign("/access-denied");
    }

    const detail = error.response?.data?.detail;
    if (!error.response) error.userMessage = "API server is unavailable. Start the backend and retry.";
    else if (typeof detail === "string") error.userMessage = detail;
    else if (status === 404) error.userMessage = "Requested resource was not found.";
    else if (status >= 500) error.userMessage = "Server error. Please try again.";
    else error.userMessage = "Request failed. Please retry.";
    return Promise.reject(error);
  },
);

export function login(email, password) {
  const formData = new FormData();
  formData.append("username", email);
  formData.append("password", password);
  return api.post("/auth/login", formData);
}

export const register = (payload) => api.post("/auth/register", payload);
export const getMe = () => api.get("/auth/me");
export const completeOnboarding = (payload) => api.patch("/auth/onboarding", payload);
export const getHealth = () => api.get("/health");
export const getRecruiterStats = () => api.get("/dashboard/recruiter-stats");
export const getMyDocuments = () => api.get("/documents/my-documents");
export const getDocumentTimeline = (documentId) => api.get(`/documents/${documentId}/timeline`);
export const getDocumentSignedUrl = (documentId) => api.get(`/documents/${documentId}/signed-url`);
export const getVerificationResult = (documentId) => api.get(`/verification/documents/${documentId}/result`);
export const runFullCheck = (documentId) => api.post(`/verification/${documentId}/full-check`, null, { timeout: LONG_REQUEST_TIMEOUT });
export const runAgentVerify = (documentId) => api.post(`/agent/verify/${documentId}`, null, { timeout: LONG_REQUEST_TIMEOUT });
export const downloadVerificationReport = (verificationId) => api.get(`/verification/${verificationId}/report`, { responseType: "blob", timeout: LONG_REQUEST_TIMEOUT });
export const getVerificationExplanations = (verificationId) => api.get(`/verification/${verificationId}/explanations`);
export const getResearchMetrics = () => api.get("/research/metrics");
export const getNotifications = () => api.get("/notifications");
export const markNotificationRead = (id) => api.patch(`/notifications/${id}/read`);
export const markAllNotificationsRead = () => api.patch("/notifications/read-all");
export const getCurrentWorkspace = () => api.get("/workspaces/current");
export const getSystemSettings = () => api.get("/settings");
export const updateSystemSettings = (payload) => api.patch("/settings", payload);
export const updateProfileSettings = (payload) => api.patch("/settings/profile", payload);
export const listInstitutionCertificates = () => api.get("/institution/certificates");
export const issueInstitutionCertificate = (payload) => api.post("/institution/certificates/issue", payload);
export const revokeCertificate = (id) => api.patch(`/institution/certificates/${id}/revoke`);
export const getCertificateLedger = (certificateId) => api.get(`/certificates/${certificateId}/ledger`);
export const publicVerifyCertificate = (certificateId) => api.get(`/public/verify/${certificateId}`);
export const publicGetTrustPassport = (slug) => api.get(`/public/passport/${slug}`);
export const listCandidates = () => api.get("/candidates");
export const createCandidate = (payload) => api.post("/candidates", payload);
export const getCandidate = (candidateId) => api.get(`/candidates/${candidateId}`);
export const generateCandidatePassport = (candidateId) => api.post(`/candidates/${candidateId}/generate-passport`);
export const getCandidatePassport = (candidateId) => api.get(`/candidates/${candidateId}/passport`);
export const createTrustPassport = (payload) => api.post("/candidates/trust-passport", payload);
export const uploadBatch = ({ batchName, documentType, files, onUploadProgress }) => {
  const formData = new FormData();
  formData.append("batch_name", batchName);
  formData.append("document_type", documentType);
  files.forEach((file) => formData.append("files", file));
  return api.post("/batch/upload", formData, { headers: { "Content-Type": "multipart/form-data" }, onUploadProgress, timeout: LONG_REQUEST_TIMEOUT });
};
export const verifyBatch = (batchId) => api.post(`/batch/${batchId}/verify`, null, { timeout: LONG_REQUEST_TIMEOUT });
export const getBatchResults = (batchId) => api.get(`/batch/${batchId}/results`);
export const downloadBatchCsv = (batchId) => api.get(`/batch/${batchId}/export-csv`, { responseType: "blob" });
export const getManualReviews = (params = {}) => api.get("/reviews", { params });
export const decideManualReview = (reviewId, payload) => api.patch(`/reviews/${reviewId}/decision`, payload);
export const createManualReview = (payload) => api.post("/reviews/create", payload);
export const runResumeConsistency = (payload) => api.post("/verification/resume-consistency", payload);
export const getAuditLogs = (params = {}) => api.get("/admin/audit-logs", { params });

export function uploadDocument({ file, documentType, onUploadProgress }) {
  const formData = new FormData();
  formData.append("document_type", documentType);
  formData.append("file", file);
  return api.post("/documents/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress,
    timeout: 60000,
  });
}

export default api;
