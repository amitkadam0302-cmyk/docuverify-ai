from typing import Any


def generate_issue_explanations(flags: list[dict[str, Any]]) -> list[dict[str, Any]]:
    explanations = []
    for flag in flags:
        flag_type = flag.get("flag_type", "authenticity_signal")
        severity = flag.get("severity", "medium")
        module = module_from_flag(flag_type)
        title = title_from_flag(flag_type)
        evidence = flag.get("message") or "The verification engine detected an authenticity signal."
        explanations.append(
            {
                "issue_title": title,
                "detected_by": module,
                "detected_by_module": module,
                "severity": severity,
                "evidence": evidence,
                "why_it_matters": why_it_matters(module, severity),
                "recommended_action": recommended_action(module, severity),
            }
        )
    if not explanations:
        explanations.append(
            {
                "issue_title": "No material fraud signals detected",
                "detected_by": "Scoring Engine",
                "detected_by_module": "Scoring Engine",
                "severity": "info",
                "evidence": "Automated checks did not create fraud flags for this verification.",
                "why_it_matters": "A clean automated result helps recruiters prioritize documents that need deeper review.",
                "recommended_action": "Proceed with normal HR controls and retain the generated verification report.",
            }
        )
    return explanations


def module_from_flag(flag_type: str) -> str:
    if flag_type.startswith("qr_"):
        return "QR / Certificate ID Verification"
    if flag_type.startswith("hash_"):
        return "SHA-256 Hash Verification"
    if flag_type.startswith("metadata_"):
        return "Metadata Forensics"
    if flag_type.startswith("tamper_"):
        return "Computer Vision Tamper Detection"
    if flag_type.startswith("resume_"):
        return "Resume Consistency Checker"
    return "Authenticity Scoring Engine"


def title_from_flag(flag_type: str) -> str:
    return flag_type.replace("_", " ").replace("qr", "QR").replace("id", "ID").title()


def why_it_matters(module: str, severity: str) -> str:
    if "Hash" in module:
        return "Hash mismatches can indicate that the uploaded file is not byte-for-byte identical to the issued document."
    if "QR" in module:
        return "QR or certificate ID issues reduce confidence that the document maps to a trusted issuer record."
    if "Metadata" in module:
        return "Metadata anomalies can reveal edits, unusual creator tools, or timeline inconsistencies."
    if "Tamper" in module:
        return "Visual anomalies can indicate pasted fields, altered stamps, edited signatures, or recompressed regions."
    if "Resume" in module:
        return "Unsupported or inconsistent career claims can create hiring and compliance risk."
    return f"This {severity} signal should be reviewed before a final business decision."


def recommended_action(module: str, severity: str) -> str:
    if severity in {"critical", "high"}:
        return "Route to manual review and verify the claim directly with the issuing institution or employer."
    if severity == "medium":
        return "Request supporting evidence and review the document before approval."
    return "Record the signal and continue with standard verification controls."
