import { create } from "zustand";

interface AppState {
  sidebarOpen: boolean;
  currentPage: string;
  stats: {
    total: number; new: number; scored: number; applied: number;
    replied: number; interview: number; offer: number;
    strong_recommend: number; recommend: number;
  };
  logLines: string[];
  setSidebarOpen: (open: boolean) => void;
  setCurrentPage: (page: string) => void;
  setStats: (stats: AppState["stats"]) => void;
  addLog: (line: string) => void;
  clearLogs: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  sidebarOpen: true,
  currentPage: "/",
  stats: { total: 0, new: 0, scored: 0, applied: 0, replied: 0, interview: 0, offer: 0, strong_recommend: 0, recommend: 0 },
  logLines: [],
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  setCurrentPage: (page) => set({ currentPage: page }),
  setStats: (stats) => set({ stats }),
  addLog: (line) => set((s) => ({ logLines: [...s.logLines.slice(-499), line] })),
  clearLogs: () => set({ logLines: [] }),
}));
