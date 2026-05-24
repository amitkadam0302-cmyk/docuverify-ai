# DocuVerify AI Career Brief

DocuVerify AI is an enterprise document trust platform that verifies certificates, resumes, experience letters, and supporting documents with OCR, computer vision, metadata review, QR validation, SHA-256 hashing, inconsistency detection, and candidate trust scoring.

## Resume Bullets

- Built a full-stack AI document verification platform using React, FastAPI, SQLAlchemy, PostgreSQL, JWT authentication, and Docker.
- Implemented multi-layer authenticity checks including OCR extraction, metadata review, QR validation, hash integrity, visual tamper detection, and fraud scoring.
- Designed role-based workflows for recruiters, institution admins, candidates, and platform admins with protected routes and JWT access control.
- Developed candidate-level trust scoring, Trust Passport sharing, batch verification, manual review queue, audit logs, notifications, and PDF/CSV report generation.
- Created a premium SaaS interface with responsive dashboards, risk score visualization, fraud heatmaps, verification timelines, and clean review workflows.

## Repository Description

AI-powered document trust platform for verifying certificates, resumes, experience letters, and sensitive documents using OCR, metadata review, QR validation, hash integrity, tamper detection, and candidate trust scoring.

## Product Walkthrough Script

DocuVerify AI helps recruiters, institutions, and verification teams validate documents with a multi-layer trust workflow. A user uploads a document, the platform extracts text, reviews metadata, validates QR and certificate records, checks hash integrity, detects visual tamper signals, and generates a trust score with clear review notes. Medium-risk and high-risk cases can be routed to manual review, while candidates can maintain a Trust Passport containing verified credentials.

## Interview Explanation

DocuVerify AI is a full-stack AI verification platform focused on document trust. I built it with a React and Vite frontend, a FastAPI backend, SQLAlchemy models, PostgreSQL persistence, JWT role access, and Docker deployment. The core engineering challenge was combining deterministic verification methods with AI-assisted document intelligence. The platform calculates a trust score from OCR consistency, metadata signals, QR and certificate ID validation, hash comparison, tamper detection, and institution matching. It also supports recruiter workflows such as batch verification, manual review, report generation, audit logs, and candidate trust profiles.

## Technical Discussion Points

**How does hash verification work?**  
The platform calculates a SHA-256 hash for every uploaded file and compares it against the stored certificate hash when a matching certificate record exists. Any content change produces a different hash.

**How does tamper detection work?**  
The service converts the document to an image and applies heuristic checks for compression anomalies, blur variance, edge inconsistency, noise inconsistency, rectangular pasted regions, and text-region mismatch. Results are shown as heatmap regions for reviewer triage.

**How is role access handled?**  
JWT tokens include user identity and role. Backend dependencies enforce permissions, and the frontend shows route access based on the authenticated role.

**Why combine multiple verification signals?**  
No single signal is reliable for every document. QR, hash, OCR, metadata, and visual checks provide complementary evidence, which produces a clearer risk assessment.

**How can this scale?**  
The architecture can move document storage to S3-compatible object storage, PostgreSQL to a managed database, OCR and CV jobs to background workers, and logs to centralized monitoring.
