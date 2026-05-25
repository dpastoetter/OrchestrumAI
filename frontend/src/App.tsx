import { Link, Route, Routes } from "react-router-dom";
import { RequestDetail } from "./views/RequestDetail";
import { RequestList } from "./views/RequestList";
import { Settings } from "./views/Settings";
import { SubmitRequest } from "./views/SubmitRequest";

export default function App() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <header className="mb-8 flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">OpenMiniAgents</h1>
          <p className="text-sm text-slate-400">ADK workflow agents — submit, approve, track</p>
        </div>
        <nav className="flex gap-4 text-sm">
          <Link className="text-sky-400 hover:underline" to="/">
            Requests
          </Link>
          <Link className="text-sky-400 hover:underline" to="/submit">
            New request
          </Link>
          <Link className="text-sky-400 hover:underline" to="/settings">
            AI providers
          </Link>
        </nav>
      </header>
      <Routes>
        <Route path="/" element={<RequestList />} />
        <Route path="/submit" element={<SubmitRequest />} />
        <Route path="/requests/:id" element={<RequestDetail />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </div>
  );
}
