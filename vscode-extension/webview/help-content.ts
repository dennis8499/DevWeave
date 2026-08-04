export interface HelpSection {
  title: string;
  paragraphs: string[];
  items?: string[];
}

export const helpContent: readonly HelpSection[] = [
  {
    title: "認識 DevWeave",
    paragraphs: [
      "DevWeave 是 repository 內建的 SDLC router，將需求、設計、任務、驗證與人工核准保留為可追溯的 work item。Extension 顯示的是檔案 snapshot，不是 engine 的權威狀態。",
      "公開 router 只有 DevWeave；grill-me、grilling、codebase-design、diagnosing-bugs 與 tdd 是階段內 companion methods。"
    ]
  },
  {
    title: "初始化與補齊",
    paragraphs: [
      "初始化會在你確認後建立固定的 DevWeave control bundle：六組 skills、AGENTS.md、skills-lock.json、hook、project、baseline 與 Wiki starter。",
      "如果 workspace 只有部分內容，Extension 只會建立缺少且沒有衝突的檔案；既有不同內容永不覆寫，結果會標示 partial 或 conflict。"
    ],
    items: [
      "0.2.0 bundle 不會把 README、docs、產品 source、tests、fixtures、work item 或歷史紀錄寫入 workspace。",
      "初始化寫入失敗時，Extension 會回復本次新建立的檔案；既有檔案保持不變。"
    ]
  },
  {
    title: "Workflow 與三道 Gate",
    paragraphs: [
      "DevWeave workflow 依序經過 requirements、scope_review、design、build_review、implementation、verification、acceptance_review 與 closed。",
      "G1 / scope 核准需求與範圍；G2 / build 核准設計與計畫；G3 / acceptance 檢查 diff、驗證、evidence、baseline、Wiki 與驗收矩陣。"
    ]
  },
  {
    title: "Wiki-first 與搜尋",
    paragraphs: [
      "Wiki 搜尋會比對標題、路徑與摘要，採大小寫不敏感的包含式查詢。輸入期間不會重建輸入框，按 Enter 才套用文字搜尋；分類篩選是精確 type match。",
      "Extension 只顯示 Wiki projection；可重用的知識更新要在 verification 依 Knowledge Review promote。"
    ]
  },
  {
    title: "Companion Skills",
    paragraphs: [
      "grill-me／grilling 用於需求釐清，codebase-design 用於 G2 設計，diagnosing-bugs 用於診斷，tdd 用於已有 G2 核准後的實作。它們不建立第二套 lifecycle，也不能取代 DevWeave gate。"
    ]
  },
  {
    title: "安全邊界",
    paragraphs: [
      "Extension 不執行 Python、CLI、shell、Git、process 或 network；公開操作先預覽，再由你複製到 Codex Chat。Bootstrap 是唯一會在確認後寫入固定路徑的操作。",
      "所有 bootstrap path 經過 normalization、manifest byte length／SHA-256 驗證與 non-overwrite 檢查；Webview 受 CSP 保護。"
    ]
  }
];
