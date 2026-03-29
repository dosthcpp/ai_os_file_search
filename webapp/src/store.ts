import { create } from 'zustand';

export type WindowType = 'file-tree' | 'file-search' | 'file-content' | 'version-history' | 'security-audit' | 'settings';

export interface WindowInstance {
  id: string;
  type: WindowType;
  title: string;
  isOpen: boolean;
  isMinimized: boolean;
  isMaximized: boolean;
  zIndex: number;
  params?: any;
}

interface OSState {
  windows: WindowInstance[];
  activeWindowId: string | null;
  nextZIndex: number;
  openWindow: (type: WindowType, title: string, params?: any) => void;
  closeWindow: (id: string) => void;
  minimizeWindow: (id: string) => void;
  maximizeWindow: (id: string) => void;
  focusWindow: (id: string) => void;
  restoreWindow: (id: string) => void;
}

export const useOSStore = create<OSState>((set, get) => ({
  windows: [],
  activeWindowId: null,
  nextZIndex: 100,

  openWindow: (type, title, params) => {
    const { windows, nextZIndex } = get();
    
    // For single-instance windows like file-tree, search, etc., focus if already open
    if (['file-tree', 'file-search', 'security-audit', 'settings'].includes(type)) {
      const existing = windows.find(w => w.type === type);
      if (existing) {
        get().focusWindow(existing.id);
        get().restoreWindow(existing.id);
        return;
      }
    }

    // For file-content, if it's the same file, focus it
    if (type === 'file-content' || type === 'version-history') {
        const existing = windows.find(w => w.type === type && w.params?.path === params?.path);
        if (existing) {
            get().focusWindow(existing.id);
            get().restoreWindow(existing.id);
            return;
        }
    }

    const newId = Math.random().toString(36).substring(7);
    const newWindow: WindowInstance = {
      id: newId,
      type,
      title,
      isOpen: true,
      isMinimized: false,
      isMaximized: false,
      zIndex: nextZIndex,
      params,
    };

    set({
      windows: [...windows, newWindow],
      activeWindowId: newId,
      nextZIndex: nextZIndex + 1,
    });
  },

  closeWindow: (id) => {
    set((state) => ({
      windows: state.windows.filter((w) => w.id !== id),
      activeWindowId: state.activeWindowId === id ? null : state.activeWindowId,
    }));
  },

  minimizeWindow: (id) => {
    set((state) => ({
      windows: state.windows.map((w) =>
        w.id === id ? { ...w, isMinimized: true } : w
      ),
      activeWindowId: state.activeWindowId === id ? null : state.activeWindowId,
    }));
  },

  maximizeWindow: (id) => {
    set((state) => ({
      windows: state.windows.map((w) =>
        w.id === id ? { ...w, isMaximized: !w.isMaximized } : w
      ),
    }));
  },

  focusWindow: (id) => {
    const { nextZIndex } = get();
    set((state) => ({
      windows: state.windows.map((w) =>
        w.id === id ? { ...w, zIndex: nextZIndex, isMinimized: false } : w
      ),
      activeWindowId: id,
      nextZIndex: nextZIndex + 1,
    }));
  },

  restoreWindow: (id) => {
    set((state) => ({
      windows: state.windows.map((w) =>
        w.id === id ? { ...w, isMinimized: false } : w
      ),
    }));
    get().focusWindow(id);
  },
}));
