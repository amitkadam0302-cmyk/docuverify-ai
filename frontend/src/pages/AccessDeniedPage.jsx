import { Link } from "react-router-dom";

import { Button, Card } from "../components/ui.jsx";

export default function AccessDeniedPage() {
  return (
    <main className="grid min-h-screen place-items-center bg-[#F5F5F7] px-5 text-center dark:bg-black">
      <Card className="max-w-md">
        <h1 className="text-2xl font-semibold">Access Denied</h1>
        <p className="mt-3 text-sm text-[#6E6E73] dark:text-[#A1A1A6]">Your account does not have access to this page.</p>
        <Link to="/app" className="mt-5 inline-flex"><Button>Back to Dashboard</Button></Link>
      </Card>
    </main>
  );
}
