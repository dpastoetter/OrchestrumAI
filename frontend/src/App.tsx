import { Route, Routes } from "react-router-dom";
import { AppLayout } from "./components/AppLayout";
import { InboxProvider } from "./context/InboxContext";
import { WorkflowPreferencesProvider } from "./context/WorkflowPreferencesContext";
import { RequestDetail } from "./views/RequestDetail";
import { RequestList } from "./views/RequestList";
import { Settings } from "./views/Settings";
import { SubmitRequest } from "./views/SubmitRequest";
import { Workflows } from "./views/Workflows";

export default function App() {
  return (
    <InboxProvider>
    <WorkflowPreferencesProvider>
    <AppLayout>
      <Routes>
        <Route path="/" element={<RequestList />} />
        <Route path="/workflows" element={<Workflows />} />
        <Route path="/submit" element={<SubmitRequest />} />
        <Route path="/requests/:id" element={<RequestDetail />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </AppLayout>
    </WorkflowPreferencesProvider>
    </InboxProvider>
  );
}
