import type { DashboardSection } from "./model";

export const dashboardSectionDefinitions: readonly [DashboardSection, string, string][] = [
  ["overview", "總覽", "先了解 workspace 與下一步"],
  ["work", "工作項目", "查看進行中與歷史工作"],
  ["knowledge", "知識", "查看 Wiki 與待更新頁面"],
  ["verification", "驗證與稽核", "查看 reviewer readiness 與事件時間軸"],
  ["help", "說明", "查看 Extension 內嵌使用手冊"]
];

const dashboardSectionIds = dashboardSectionDefinitions.map(([section]) => section);

export function moveDashboardSection(current: DashboardSection, key: string): DashboardSection | null {
  if (!["ArrowRight", "ArrowDown", "ArrowLeft", "ArrowUp", "Home", "End"].includes(key)) return null;
  const currentIndex = dashboardSectionIds.indexOf(current);
  if (currentIndex < 0) return null;
  const nextIndex = key === "Home"
    ? 0
    : key === "End"
      ? dashboardSectionIds.length - 1
      : (currentIndex + (key === "ArrowLeft" || key === "ArrowUp" ? -1 : 1) + dashboardSectionIds.length) % dashboardSectionIds.length;
  return dashboardSectionIds[nextIndex] ?? null;
}

export function dashboardPanelState(section: DashboardSection, selected: DashboardSection): {
  id: string;
  labelledBy: string;
  tabIndex: 0 | -1;
  hidden: boolean;
} {
  const active = section === selected;
  return {
    id: `tabpanel-${section}`,
    labelledBy: `section-tab-${section}`,
    tabIndex: active ? 0 : -1,
    hidden: !active
  };
}
