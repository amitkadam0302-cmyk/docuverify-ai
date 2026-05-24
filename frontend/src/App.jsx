import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { LoadingSpinner } from "./components/ui.jsx";
import { useAuth } from "./context/AuthContext.jsx";
import DashboardLayout from "./layouts/DashboardLayout.jsx";
import AccessDeniedPage from "./pages/AccessDeniedPage.jsx";
import BatchVerificationPage from "./pages/BatchVerificationPage.jsx";
import CandidateProfilePage from "./pages/CandidateProfilePage.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import DocumentUploadPage from "./pages/DocumentUploadPage.jsx";
import InstitutionPortalPage from "./pages/InstitutionPortalPage.jsx";
import LandingPage from "./pages/LandingPage.jsx";
import LegalPage from "./pages/LegalPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import ManualReviewQueuePage from "./pages/ManualReviewQueuePage.jsx";
import NotFoundPage from "./pages/NotFoundPage.jsx";
import OnboardingPage from "./pages/OnboardingPage.jsx";
import PublicCertificateVerificationPage from "./pages/PublicCertificateVerificationPage.jsx";
import PublicTrustPassportPage from "./pages/PublicTrustPassportPage.jsx";
import RecruiterDashboardPage from "./pages/RecruiterDashboardPage.jsx";
import RegisterPage from "./pages/RegisterPage.jsx";
import ResearchMetricsPage from "./pages/ResearchMetricsPage.jsx";
import ResumeConsistencyPage from "./pages/ResumeConsistencyPage.jsx";
import SettingsPage from "./pages/SettingsPage.jsx";
import TrustPassportPage from "./pages/TrustPassportPage.jsx";
import VerificationHistoryPage from "./pages/VerificationHistoryPage.jsx";
import VerificationResultPage from "./pages/VerificationResultPage.jsx";

function ProtectedRoute({ children }) {
  const { isAuthenticated, loading, user } = useAuth();
  const location = useLocation();
  if (loading) return <LoadingSpinner label="Preparing workspace" />;
  if (!isAuthenticated) return <Navigate to="/login" state={{ from: location }} replace />;
  if (user && !user.onboarding_completed && location.pathname !== "/onboarding") return <Navigate to="/onboarding" replace />;
  return children;
}

function PublicOnlyRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <LoadingSpinner label="Preparing workspace" />;
  if (isAuthenticated) return <Navigate to="/app" replace />;
  return children;
}

function RoleRoute({ roles, children }) {
  const { user, loading } = useAuth();
  if (loading) return <LoadingSpinner label="Checking access" />;
  if (user?.role === "super_admin" || roles.includes(user?.role)) return children;
  return <AccessDeniedPage />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<PublicOnlyRoute><LoginPage /></PublicOnlyRoute>} />
      <Route path="/register" element={<PublicOnlyRoute><RegisterPage /></PublicOnlyRoute>} />
      <Route path="/access-denied" element={<AccessDeniedPage />} />
      <Route path="/privacy" element={<LegalPage type="privacy" />} />
      <Route path="/terms" element={<LegalPage type="terms" />} />
      <Route path="/security" element={<LegalPage type="security" />} />
      <Route path="/contact" element={<LegalPage type="contact" />} />
      <Route path="/support" element={<LegalPage type="contact" />} />
      <Route path="/onboarding" element={<ProtectedRoute><OnboardingPage /></ProtectedRoute>} />
      <Route path="/verify" element={<Navigate to="/app/upload" replace />} />
      <Route path="/verify/:certificateId" element={<PublicCertificateVerificationPage />} />
      <Route path="/passport/:slug" element={<PublicTrustPassportPage />} />

      <Route path="/app" element={<ProtectedRoute><DashboardLayout /></ProtectedRoute>}>
        <Route index element={<Dashboard />} />
        <Route path="upload" element={<DocumentUploadPage />} />
        <Route path="history" element={<VerificationHistoryPage />} />
        <Route path="results" element={<VerificationHistoryPage />} />
        <Route path="results/:documentId" element={<VerificationResultPage />} />
        <Route path="resume-consistency" element={<RoleRoute roles={["recruiter", "company_admin"]}><ResumeConsistencyPage /></RoleRoute>} />
        <Route path="batch" element={<RoleRoute roles={["recruiter", "company_admin"]}><BatchVerificationPage /></RoleRoute>} />
        <Route path="manual-reviews" element={<RoleRoute roles={["recruiter", "company_admin", "institution_admin"]}><ManualReviewQueuePage /></RoleRoute>} />
        <Route path="candidates" element={<RoleRoute roles={["recruiter", "company_admin"]}><CandidateProfilePage /></RoleRoute>} />
        <Route path="trust-passport" element={<TrustPassportPage />} />
        <Route path="institution" element={<RoleRoute roles={["institution_admin"]}><InstitutionPortalPage /></RoleRoute>} />
        <Route path="recruiter" element={<RoleRoute roles={["recruiter", "company_admin"]}><RecruiterDashboardPage /></RoleRoute>} />
        <Route path="research" element={<RoleRoute roles={["recruiter", "company_admin", "institution_admin"]}><ResearchMetricsPage /></RoleRoute>} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>

      <Route element={<ProtectedRoute><DashboardLayout /></ProtectedRoute>}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/upload" element={<DocumentUploadPage />} />
        <Route path="/history" element={<VerificationHistoryPage />} />
        <Route path="/results" element={<VerificationHistoryPage />} />
        <Route path="/results/:documentId" element={<VerificationResultPage />} />
        <Route path="/verification/:documentId" element={<VerificationResultPage />} />
        <Route path="/candidates" element={<RoleRoute roles={["recruiter", "company_admin"]}><CandidateProfilePage /></RoleRoute>} />
        <Route path="/candidates/:candidateId" element={<RoleRoute roles={["recruiter", "company_admin"]}><CandidateProfilePage /></RoleRoute>} />
        <Route path="/trust-passport" element={<TrustPassportPage />} />
        <Route path="/batch" element={<RoleRoute roles={["recruiter", "company_admin"]}><BatchVerificationPage /></RoleRoute>} />
        <Route path="/review-queue" element={<RoleRoute roles={["recruiter", "company_admin", "institution_admin"]}><ManualReviewQueuePage /></RoleRoute>} />
        <Route path="/institution" element={<RoleRoute roles={["institution_admin"]}><InstitutionPortalPage /></RoleRoute>} />
        <Route path="/analytics" element={<RoleRoute roles={["recruiter", "company_admin"]}><RecruiterDashboardPage /></RoleRoute>} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
