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
      "0.2.2 bundle 不會把 README、docs、產品 source、tests、fixtures、work item 或歷史紀錄寫入 workspace；既有 0.2.1 artifact 保留在 repository。",
      "按「取消」或初始化寫入失敗時，Extension 會回復本次新建立的檔案；既有檔案保持不變，不留下 partial control bundle。"
    ]
  },
  {
    title: "Windows 安裝與認證範圍",
    paragraphs: [
      "本次提供 0.2.2 VSIX。請在 VS Code Extensions 的 `...` 選單選擇 Install from VSIX…，安裝 repository 內的 `devweave-control-center-0.2.2.vsix`；既有 0.2.1 artifact 保留，再從 Activity Bar 開啟 Control Center。",
      "本次認證環境是 Windows x64 build 10.0.26200／25H2、VS Code 1.131.0、Python 3.14.6、Git 2.51.0.windows.1 與目前 Codex host；驗收基準為 Python full suite 103 項與 Extension unit tests 77 項。",
      "VS Code 1.90+ 與 Python 3.11+ 只是技術門檻。本公開版不包含 Marketplace 上架，也不承諾 macOS/Linux 支援。",
      "若發生發布事故，立即停止散布並停用或解除安裝 0.2.2；這些操作不會自動刪除 `.devweave`、Wiki 或 workspace 資料。"
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
    title: "Preview、Refresh 與多 work",
    paragraphs: [
      "公開操作請依序完成：選擇 work 或 task →「預覽公開操作」→確認 prompt →「複製 prompt」→到 Codex Chat 貼上、審閱並送出→回到 Extension「重新整理檔案快照」。",
      "Preview 綁定目前 panel、intent 與 snapshot revision。Refresh、切換 work、初始化結果或 snapshot 更新後，舊 prompt 會失效，必須重新預覽；clipboard 暫時失敗時可在同一個 preview 重試一次。"
    ],
    items: [
      "既有 `devweave.copyNextAction` 只會開啟 Control Center，不再直接複製。",
      "單一 active work 會自動顯示 next preview；多個 active work 必須先明確選取；沒有 active work 時會引導建立或選取。",
      "`status` 可以明確查詢全部 active work；`next` 不會猜測多 work 的目標。"
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
