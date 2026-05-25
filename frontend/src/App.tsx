import { NavLink, Route, Routes } from "react-router-dom";
import { RequestDetail } from "./views/RequestDetail";
import { RequestList } from "./views/RequestList";
import { Settings } from "./views/Settings";
import { SubmitRequest } from "./views/SubmitRequest";

const navLink =
  "rounded-lg px-3 py-1.5 text-sm transition text-slate-400 hover:text-slate-200 hover:bg-slate-800/60";
const navActive = "!text-sky-300 !bg-sky-950/50 ring-1 ring-sky-800/50";

export default function App() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <header className="mb-8 flex flex-col gap-4 border-b border-slate-800/80 pb-6 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-50">OpenMiniAgents</h1>
          <p className="text-sm text-slate-400">ADK workflow agents — submit, approve, track</p>
        </div>
        <nav className="flex flex-wrap gap-1">
          <NavLink to="/" end className={({ isActive }) => `${navLink} ${isActive ? navActive : ""}`}>
            Requests
          </NavLink>
          <NavLink to="/submit" className={({ isActive }) => `${navLink} ${isActive ? navActive : ""}`}>
            New request
          </NavLink>
          <NavLink to="/settings" className={({ isActive }) => `${navLink} ${isActive ? navActive : ""}`}>
            AI providers
          </NavLink>
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
