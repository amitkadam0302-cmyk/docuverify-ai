import { useEffect, useState } from "react";

import { Badge, Button, Card, Select, Toast } from "../components/ui.jsx";
import { decideManualReview, getManualReviews } from "../services/api.js";

export default function ManualReviewQueuePage() {
  const [reviews, setReviews] = useState([]);
  const [status, setStatus] = useState("");
  const [message, setMessage] = useState("");
  const load = () => getManualReviews(status ? { status_filter: status } : {}).then((response) => setReviews(response.data)).catch(() => setReviews([]));
  useEffect(() => { load(); }, [status]);

  async function decide(id, finalDecision) {
    await decideManualReview(id, { final_decision: finalDecision, reviewer_comment: "" }).then(() => setMessage("Review updated.")).catch((error) => setMessage(error.userMessage || "Review update failed."));
    load();
  }

  return (
    <div className="space-y-6">
      <Card className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"><div><Badge tone="info">Review</Badge><h1 className="mt-3 text-2xl font-semibold">Review Queue</h1></div><Select value={status} onChange={(e) => setStatus(e.target.value)}><option value="">All statuses</option><option value="pending">Pending</option><option value="in_review">In Review</option><option value="approved">Approved</option><option value="rejected">Rejected</option></Select></Card>
      <Toast message={message} />
      <Card className="space-y-3">
        {reviews.length ? reviews.map((review) => <div key={review.id} className="rounded-2xl bg-black/5 p-4 dark:bg-white/10"><div className="flex flex-wrap items-center justify-between gap-3"><p className="font-semibold">Document #{review.document_id}</p><Badge>{review.status}</Badge></div><p className="mt-1 text-sm text-[#6E6E73] dark:text-[#A1A1A6]">Priority: {review.priority}</p><div className="mt-3 flex gap-2"><Button variant="success" onClick={() => decide(review.id, "approved")}>Approve</Button><Button variant="danger" onClick={() => decide(review.id, "rejected")}>Reject</Button></div></div>) : <p className="text-sm text-[#6E6E73] dark:text-[#A1A1A6]">No reviews pending.</p>}
      </Card>
    </div>
  );
}
