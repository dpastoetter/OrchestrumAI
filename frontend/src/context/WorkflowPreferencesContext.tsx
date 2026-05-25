import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api } from "../api";
import type { GenericWorkflowAgent } from "../types";

type WorkflowPreferencesContextValue = {
  ready: boolean;
  loadError: string | null;
  advancedMode: boolean;
  enabledGeneric: Set<string>;
  catalog: GenericWorkflowAgent[];
  refresh: () => Promise<void>;
  setAdvancedMode: (value: boolean) => Promise<void>;
  setEnabledGeneric: (ids: Set<string>) => void;
  saveWorkflowPreferences: (opts?: {
    enabled_generic_agents?: string[];
    advanced_mode?: boolean;
  }) => Promise<void>;
};

const WorkflowPreferencesContext = createContext<WorkflowPreferencesContextValue | null>(
  null,
);

export function WorkflowPreferencesProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [advancedMode, setAdvancedModeState] = useState(false);
  const [enabledGeneric, setEnabledGenericState] = useState<Set<string>>(new Set());
  const [catalog, setCatalog] = useState<GenericWorkflowAgent[]>([]);

  const refresh = useCallback(async () => {
    try {
      const [catalogRes, wfSettings] = await Promise.all([
        api.getWorkflowGenericAgents(),
        api.getWorkflowSettings(),
      ]);
      setCatalog(catalogRes.agents);
      setEnabledGenericState(new Set(wfSettings.settings.enabled_generic_agents));
      setAdvancedModeState(wfSettings.settings.advanced_mode ?? false);
      setLoadError(null);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : String(err));
    } finally {
      setReady(true);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const saveWorkflowPreferences = useCallback(
    async (opts?: { enabled_generic_agents?: string[]; advanced_mode?: boolean }) => {
      const res = await api.updateWorkflowSettings({
        enabled_generic_agents:
          opts?.enabled_generic_agents ?? [...enabledGeneric],
        advanced_mode: opts?.advanced_mode ?? advancedMode,
      });
      setEnabledGenericState(new Set(res.settings.enabled_generic_agents));
      setAdvancedModeState(res.settings.advanced_mode ?? false);
      setLoadError(null);
    },
    [advancedMode, enabledGeneric],
  );

  const setAdvancedMode = useCallback(
    async (value: boolean) => {
      const prev = advancedMode;
      setAdvancedModeState(value);
      try {
        const res = await api.updateWorkflowSettings({ advanced_mode: value });
        setAdvancedModeState(res.settings.advanced_mode ?? false);
        setLoadError(null);
      } catch (err) {
        setAdvancedModeState(prev);
        throw err;
      }
    },
    [advancedMode],
  );

  const setEnabledGeneric = useCallback((ids: Set<string>) => {
    setEnabledGenericState(ids);
  }, []);

  const value = useMemo(
    () => ({
      ready,
      loadError,
      advancedMode,
      enabledGeneric,
      catalog,
      refresh,
      setAdvancedMode,
      setEnabledGeneric,
      saveWorkflowPreferences,
    }),
    [
      ready,
      loadError,
      advancedMode,
      enabledGeneric,
      catalog,
      refresh,
      setAdvancedMode,
      setEnabledGeneric,
      saveWorkflowPreferences,
    ],
  );

  return (
    <WorkflowPreferencesContext.Provider value={value}>
      {children}
    </WorkflowPreferencesContext.Provider>
  );
}

export function useWorkflowPreferences(): WorkflowPreferencesContextValue {
  const ctx = useContext(WorkflowPreferencesContext);
  if (!ctx) {
    throw new Error("useWorkflowPreferences must be used within WorkflowPreferencesProvider");
  }
  return ctx;
}
