import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { api } from "../api";
import { countAwaitingApproval } from "../lib/requestFilters";
import type { RequestSummary } from "../types";

const NOTIFY_KEY = "orchestrumai_notify_approval";

type InboxContextValue = {
  requests: RequestSummary[];
  awaitingCount: number;
  refresh: () => Promise<void>;
  setRequests: (items: RequestSummary[]) => void;
  notifyEnabled: boolean;
  setNotifyEnabled: (v: boolean) => void;
};

const InboxContext = createContext<InboxContextValue | null>(null);

function loadNotifyPref(): boolean {
  return localStorage.getItem(NOTIFY_KEY) !== "0";
}

export function InboxProvider({ children }: { children: ReactNode }) {
  const [requests, setRequests] = useState<RequestSummary[]>([]);
  const [notifyEnabled, setNotifyEnabledState] = useState(loadNotifyPref);
  const prevAwaiting = useRef(0);
  const permissionAsked = useRef(false);

  const refresh = useCallback(async () => {
    const items = await api.listRequests();
    setRequests(items);
    return;
  }, []);

  const setNotifyEnabled = useCallback((v: boolean) => {
    localStorage.setItem(NOTIFY_KEY, v ? "1" : "0");
    setNotifyEnabledState(v);
  }, []);

  useEffect(() => {
    refresh().catch(() => {});
    const t = setInterval(() => {
      refresh().catch(() => {});
    }, 3000);
    return () => clearInterval(t);
  }, [refresh]);

  const awaitingCount = useMemo(() => countAwaitingApproval(requests), [requests]);

  useEffect(() => {
    if (!notifyEnabled || typeof Notification === "undefined") return;
    if (awaitingCount > prevAwaiting.current && awaitingCount > 0) {
      const fire = () => {
        new Notification("OrchestrumAI", {
          body: `${awaitingCount} request${awaitingCount === 1 ? "" : "s"} need your approval`,
          tag: "orchestrum-awaiting",
        });
      };
      if (Notification.permission === "granted") {
        fire();
      } else if (Notification.permission !== "denied" && !permissionAsked.current) {
        permissionAsked.current = true;
        Notification.requestPermission().then((p) => {
          if (p === "granted") fire();
        });
      }
    }
    prevAwaiting.current = awaitingCount;
  }, [awaitingCount, notifyEnabled]);

  const value = useMemo(
    () => ({
      requests,
      awaitingCount,
      refresh,
      setRequests,
      notifyEnabled,
      setNotifyEnabled,
    }),
    [requests, awaitingCount, refresh, notifyEnabled, setNotifyEnabled],
  );

  return <InboxContext.Provider value={value}>{children}</InboxContext.Provider>;
}

export function useInbox(): InboxContextValue {
  const ctx = useContext(InboxContext);
  if (!ctx) throw new Error("useInbox must be used within InboxProvider");
  return ctx;
}
