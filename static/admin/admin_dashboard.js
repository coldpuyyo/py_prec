const MODE_SCRAPE = "scrape";
const MODE_KEYWORD = "keyword";
const MODE_BLOG_SCRAPE = "blogscrape";
const MODE_TITLE = "title";

let currentPromptMode = MODE_SCRAPE;

function authExpired(status) {
  if (status === 401) {
    alert("로그인이 필요합니다.");
    location.href = "/admin/login";
    return true;
  }
  return false;
}

async function loadScrapPrompt() {
  const res = await fetch("/admin/scrapprompt/get");
  if (authExpired(res.status)) return;

  const data = await res.json();
  if (!data.ok) {
    alert(data.message || "프롬프트 로드 실패");
    return;
  }
  document.getElementById("scrapgenaratorprompt").value = data.blog_prompt || "";
}

async function loadKeywordPrompt() {
  const res = await fetch("/admin/keywordprompt/get");
  if (authExpired(res.status)) return;

  const data = await res.json();
  if (!data.ok) {
    alert(data.message || "프롬프트 로드 실패");
    return;
  }
  document.getElementById("keywordgenaratorprompt").value = data.blog_prompt || "";
}

async function loadBlogScrapPrompt() {
  const res = await fetch("/admin/blogscrapprompt/get");
  if (authExpired(res.status)) return;

  const data = await res.json();
  if (!data.ok) {
    alert(data.message || "프롬프트 로드 실패");
    return;
  }
  document.getElementById("blogscrapgenaratorprompt").value = data.blog_prompt || "";
}

async function loadTitlePrompt() {
  const res = await fetch("/admin/titleprompt/get");
  if (authExpired(res.status)) return;

  const data = await res.json();
  if (!data.ok) {
    alert(data.message || "프롬프트 로드 실패");
    return;
  }
  document.getElementById("titlegenaratorprompt").value = data.title_prompt || "";
}

async function savescrapgenaratorPrompt() {
  const prompt = document.getElementById("scrapgenaratorprompt").value;
  const res = await fetch("/admin/scrapsave-prompt", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ blog_prompt: prompt }),
  });

  if (authExpired(res.status)) return;
  const data = await res.json();
  if (!data.ok) {
    alert(data.message || "프롬프트 저장 실패");
    return;
  }
  alert("프롬프트 저장 완료");
}

async function savekeywordgenaratorPrompt() {
  const prompt = document.getElementById("keywordgenaratorprompt").value;
  const res = await fetch("/admin/keywordsave-prompt", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ blog_prompt: prompt }),
  });

  if (authExpired(res.status)) return;
  const data = await res.json();
  if (!data.ok) {
    alert(data.message || "프롬프트 저장 실패");
    return;
  }
  alert("프롬프트 저장 완료");
}

async function saveblogscrapgenaratorPrompt() {
  const prompt = document.getElementById("blogscrapgenaratorprompt").value;
  const res = await fetch("/admin/blogscrapsave-prompt", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ blog_prompt: prompt }),
  });

  if (authExpired(res.status)) return;
  const data = await res.json();
  if (!data.ok) {
    alert(data.message || "프롬프트 저장 실패");
    return;
  }
  alert("프롬프트 저장 완료");
}

async function savetitlegenaratorPrompt() {
  const prompt = document.getElementById("titlegenaratorprompt").value;
  const res = await fetch("/admin/titlesave-prompt", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title_prompt: prompt }),
  });

  if (authExpired(res.status)) return;
  const data = await res.json();
  if (!data.ok) {
    alert(data.message || "프롬프트 저장 실패");
    return;
  }
  alert("프롬프트 저장 완료");
}

async function loadApiKeyStatus() {
  const res = await fetch("/admin/api-keys/status");
  if (authExpired(res.status)) return;

  const data = await res.json();
  if (!data.ok) {
    alert(data.message || "API 키 상태 조회 실패");
    return;
  }

  document.getElementById("geminiStatus").innerText =
    data.gemini_exists ? `설정됨 (${data.gemini_masked})` : "미설정";
  document.getElementById("openaiStatus").innerText =
    data.openai_exists ? `설정됨 (${data.openai_masked})` : "미설정";
}

async function saveApiKeys() {
  const gemini_api_key = document.getElementById("geminiApiKey").value.trim();
  const openai_api_key = document.getElementById("openaiApiKey").value.trim();

  const res = await fetch("/admin/api-keys/update", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ gemini_api_key, openai_api_key }),
  });

  if (authExpired(res.status)) return;
  const data = await res.json();
  if (!data.ok) {
    alert(data.message || "API 키 저장 실패");
    return;
  }

  document.getElementById("geminiApiKey").value = "";
  document.getElementById("openaiApiKey").value = "";
  await loadApiKeyStatus();
  alert("API 키 저장 완료");
}

function renderVpnConfig(config) {
  const cfg = config || {};
  document.getElementById("vpnEnabled").checked = !!cfg.enabled;
  document.getElementById("vpnRunAsAdmin").checked = !!cfg.run_as_admin;
  document.getElementById("vpnCliDir").value = cfg.cli_dir || "";
  document.getElementById("vpnActivateBeforePublish").checked = !!cfg.activate_before_publish;
  document.getElementById("vpnConnectLocation").value = cfg.connect_location || "smart";
  document.getElementById("vpnCommandTimeoutSec").value = String(cfg.command_timeout_sec ?? 120);
  document.getElementById("vpnSettleWaitSec").value = String(cfg.settle_wait_sec ?? 3);

  const hasCode = !!cfg.has_activation_code;
  const masked = cfg.activation_code_masked || "";
  document.getElementById("vpnActivationCodeStatus").innerText =
    hasCode ? `현재 저장된 코드: ${masked}` : "현재 저장된 코드 없음";
  document.getElementById("vpnActivationCode").value = "";
}

async function loadVpnConfig() {
  const res = await fetch("/admin/vpn/config");
  if (authExpired(res.status)) return;

  const data = await res.json();
  if (!data.ok) {
    alert(data.message || "VPN 설정 조회 실패");
    return;
  }
  renderVpnConfig(data.config || {});
  document.getElementById("vpnStatus").innerText = "";
}

async function saveVpnConfig() {
  const payload = {
    enabled: document.getElementById("vpnEnabled").checked,
    run_as_admin: document.getElementById("vpnRunAsAdmin").checked,
    cli_dir: document.getElementById("vpnCliDir").value.trim(),
    activate_before_publish: document.getElementById("vpnActivateBeforePublish").checked,
    activation_code: document.getElementById("vpnActivationCode").value.trim(),
    connect_location: document.getElementById("vpnConnectLocation").value.trim() || "smart",
    command_timeout_sec: Number(document.getElementById("vpnCommandTimeoutSec").value || 120),
    settle_wait_sec: Number(document.getElementById("vpnSettleWaitSec").value || 3),
  };

  const res = await fetch("/admin/vpn/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (authExpired(res.status)) return;

  const data = await res.json();
  if (!data.ok) {
    alert(data.message || "VPN 설정 저장 실패");
    return;
  }

  renderVpnConfig(data.config || {});
  document.getElementById("vpnStatus").innerText = JSON.stringify(data, null, 2);
  alert("VPN 설정 저장 완료");
}

async function logout() {
  await fetch("/admin/logout", { method: "POST" });
  location.href = "/";
}

function togglePromptMode(mode) {
  const modes = [MODE_SCRAPE, MODE_KEYWORD, MODE_BLOG_SCRAPE, MODE_TITLE];
  currentPromptMode = modes.includes(mode) ? mode : MODE_SCRAPE;

  const modeScrapBtn = document.getElementById("modeScrapBtn");
  const modeKeywordBtn = document.getElementById("modeKeywordBtn");
  const modeBlogScrapBtn = document.getElementById("modeBlogScrapBtn");
  const modeTitleBtn = document.getElementById("modeTitleBtn");
  const scrapPrompt = document.getElementById("scrapgenaratorprompt");
  const keywordPrompt = document.getElementById("keywordgenaratorprompt");
  const blogScrapPrompt = document.getElementById("blogscrapgenaratorprompt");
  const titlePrompt = document.getElementById("titlegenaratorprompt");
  const saveScrapBtn = document.getElementById("savescrapgenaratorPromptBtn");
  const saveKeywordBtn = document.getElementById("savekeywordgenaratorPromptBtn");
  const saveBlogScrapBtn = document.getElementById("saveblogscrapgenaratorPromptBtn");
  const saveTitleBtn = document.getElementById("savetitlegenaratorPromptBtn");

  const isScrap = currentPromptMode === MODE_SCRAPE;
  const isKeyword = currentPromptMode === MODE_KEYWORD;
  const isBlogScrap = currentPromptMode === MODE_BLOG_SCRAPE;
  const isTitle = currentPromptMode === MODE_TITLE;

  scrapPrompt.hidden = !isScrap;
  keywordPrompt.hidden = !isKeyword;
  blogScrapPrompt.hidden = !isBlogScrap;
  titlePrompt.hidden = !isTitle;
  saveScrapBtn.hidden = !isScrap;
  saveKeywordBtn.hidden = !isKeyword;
  saveBlogScrapBtn.hidden = !isBlogScrap;
  saveTitleBtn.hidden = !isTitle;
  modeScrapBtn.classList.toggle("active", isScrap);
  modeKeywordBtn.classList.toggle("active", isKeyword);
  modeBlogScrapBtn.classList.toggle("active", isBlogScrap);
  modeTitleBtn.classList.toggle("active", isTitle);

  modeScrapBtn.setAttribute("aria-pressed", isScrap ? "true" : "false");
  modeKeywordBtn.setAttribute("aria-pressed", isKeyword ? "true" : "false");
  modeBlogScrapBtn.setAttribute("aria-pressed", isBlogScrap ? "true" : "false");
  modeTitleBtn.setAttribute("aria-pressed", isTitle ? "true" : "false");
}

window.addEventListener("DOMContentLoaded", async () => {
  document.getElementById("savescrapgenaratorPromptBtn").addEventListener("click", savescrapgenaratorPrompt);
  document.getElementById("savekeywordgenaratorPromptBtn").addEventListener("click", savekeywordgenaratorPrompt);
  document.getElementById("saveblogscrapgenaratorPromptBtn").addEventListener("click", saveblogscrapgenaratorPrompt);
  document.getElementById("savetitlegenaratorPromptBtn").addEventListener("click", savetitlegenaratorPrompt);
  document.getElementById("saveApiKeysBtn").addEventListener("click", saveApiKeys);
  document.getElementById("saveVpnConfigBtn").addEventListener("click", saveVpnConfig);
  document.getElementById("logoutBtn").addEventListener("click", logout);

  document.getElementById("modeScrapBtn").addEventListener("click", () => togglePromptMode(MODE_SCRAPE));
  document.getElementById("modeKeywordBtn").addEventListener("click", () => togglePromptMode(MODE_KEYWORD));
  document.getElementById("modeBlogScrapBtn").addEventListener("click", () => togglePromptMode(MODE_BLOG_SCRAPE));
  document.getElementById("modeTitleBtn").addEventListener("click", () => togglePromptMode(MODE_TITLE));

  await loadScrapPrompt();
  await loadKeywordPrompt();
  await loadBlogScrapPrompt();
  await loadTitlePrompt();
  await loadApiKeyStatus();
  await loadVpnConfig();

  togglePromptMode(MODE_SCRAPE);
});
