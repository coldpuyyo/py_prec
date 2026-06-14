const MODE_SCRAPE = "scrape";
const MODE_KEYWORD = "keyword";
const MODE_BLOG_SCRAPE = "blogscrape";

let currentGenerateMode = MODE_SCRAPE;
let isTitlePromptSettingOpen = false;

const apiStatus = {
  gemini_exists: false,
  openai_exists: false,
};
const publisherProfiles = [];

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json();
  return data;
}

function guessTitleFromGeneratedText(text) {
  const cleaned = (text || "").trim();
  if (!cleaned) return "";

  const lines = cleaned
    .split("\n")
    .map((x) => x.trim())
    .filter((x) => x.length > 0);

  if (lines.length === 0) return "";

  const first = lines[0].replace(/^#+\s*/, "").trim();
  if (first.length <= 120) return first;
  return first.slice(0, 120).trim();
}

function getResultEl() {
  return document.getElementById("result");
}

function setResultText(text) {
  const el = getResultEl();
  if (!el) return;
  if ("value" in el) {
    el.value = text ?? "";
  } else {
    el.innerText = text ?? "";
  }
}

function getResultText() {
  const el = getResultEl();
  if (!el) return "";
  if ("value" in el) {
    return String(el.value ?? "").trim();
  }
  return String(el.innerText ?? "").trim();
}

function setGenerateMode(mode) {
  const modes = [MODE_SCRAPE, MODE_KEYWORD, MODE_BLOG_SCRAPE];
  currentGenerateMode = modes.includes(mode) ? mode : MODE_SCRAPE;

  const scrapeModeArea = document.getElementById("scrapeModeArea");
  const scrapeModeArea2 = document.getElementById("scrapeModeArea2");
  const keywordModeArea = document.getElementById("keywordModeArea");
  const blogScrapeModeArea = document.getElementById("blogScrapeModeArea");
  const modeScrapeBtn = document.getElementById("modeScrapeBtn");
  const modeKeywordBtn = document.getElementById("modeKeywordBtn");
  const modeBlogScrapeBtn = document.getElementById("modeBlogScrapeBtn");
  const scrapgenaratorBtn = document.getElementById("scrapgenerateBtn");
  const keywordgenaratorBtn = document.getElementById("keywordgenerateBtn");
  const blogScrapgenaratorBtn = document.getElementById("blogScrapgenerateBtn");

  const isScrape = currentGenerateMode === MODE_SCRAPE;
  const isKeyword = currentGenerateMode === MODE_KEYWORD;
  const isBlogScrape = currentGenerateMode === MODE_BLOG_SCRAPE;

  scrapeModeArea.hidden = !isScrape;
  scrapeModeArea2.hidden = !isScrape;
  scrapgenaratorBtn.hidden = !isScrape;
  keywordgenaratorBtn.hidden = !isKeyword;
  keywordModeArea.hidden = !isKeyword;
  blogScrapeModeArea.hidden = !isBlogScrape;
  blogScrapgenaratorBtn.hidden = !isBlogScrape;

  modeScrapeBtn.classList.toggle("active", isScrape);
  modeKeywordBtn.classList.toggle("active", isKeyword);
  modeBlogScrapeBtn.classList.toggle("active", isBlogScrape);

  modeScrapeBtn.setAttribute("aria-pressed", isScrape ? "true" : "false");
  modeKeywordBtn.setAttribute("aria-pressed", isKeyword ? "true" : "false");
  modeBlogScrapeBtn.setAttribute("aria-pressed", isBlogScrape ? "true" : "false");
}

async function loadCategories() {
  const categorySelect = document.getElementById("category");
  categorySelect.innerHTML = "";

  const data = await fetchJson("/user/categories");
  if (!data.ok || !Array.isArray(data.categories)) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.text = "카테고리 로드 실패";
    categorySelect.appendChild(opt);
    return;
  }

  data.categories.forEach((c) => {
    const opt = document.createElement("option");
    opt.value = c;
    opt.text = c;
    categorySelect.appendChild(opt);
  });
}

async function fetchApiStatus() {
  const data = await fetchJson("/user/api-keys/status");
  apiStatus.gemini_exists = !!data.gemini_exists;
  apiStatus.openai_exists = !!data.openai_exists;
}

function applyProviderAvailability() {
  const providerSelect = document.getElementById("provider");
  const geminiOpt = providerSelect.querySelector("option[value='gemini']");
  const gptOpt = providerSelect.querySelector("option[value='gpt']");

  geminiOpt.disabled = !apiStatus.gemini_exists;
  gptOpt.disabled = !apiStatus.openai_exists;

  if (providerSelect.value === "gemini" && geminiOpt.disabled && !gptOpt.disabled) {
    providerSelect.value = "gpt";
  }
  if (providerSelect.value === "gpt" && gptOpt.disabled && !geminiOpt.disabled) {
    providerSelect.value = "gemini";
  }
}

async function loadModelsByProvider() {
  const provider = document.getElementById("provider").value;
  const modelSelect = document.getElementById("model");
  modelSelect.innerHTML = "";

  const data = await fetchJson(`/user/models?provider=${encodeURIComponent(provider)}`);
  if (!data.ok || !Array.isArray(data.models) || data.models.length === 0) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.text = "사용 가능한 모델 없음";
    modelSelect.appendChild(opt);
    return;
  }

  data.models.forEach((modelName) => {
    const opt = document.createElement("option");
    opt.value = modelName;
    opt.text = modelName;
    modelSelect.appendChild(opt);
  });
}

async function ensureApiKeySetup() {
  await fetchApiStatus();
  applyProviderAvailability();

  const modal = document.getElementById("apiKeyModal");
  const geminiRow = document.getElementById("geminiRow");
  const openaiRow = document.getElementById("openaiRow");

  if (apiStatus.gemini_exists && apiStatus.openai_exists) {
    modal.style.display = "none";
    return true;
  }

  geminiRow.style.display = apiStatus.gemini_exists ? "none" : "block";
  openaiRow.style.display = apiStatus.openai_exists ? "none" : "block";
  modal.style.display = "block";
  return false;
}

async function saveApiKeys() {
  const geminiKey = document.getElementById("geminiApiKey").value.trim();
  const openaiKey = document.getElementById("openaiApiKey").value.trim();

  const data = await fetchJson("/user/api-keys/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      gemini_api_key: geminiKey,
      openai_api_key: openaiKey,
    }),
  });

  if (!data.ok) {
    alert(data.message || "API 키 저장 실패");
    return;
  }

  document.getElementById("geminiApiKey").value = "";
  document.getElementById("openaiApiKey").value = "";

  await ensureApiKeySetup();
  await loadModelsByProvider();
  alert("API 키 저장 완료");
}

async function loadPublisherProfiles() {
  const select = document.getElementById("publisherProfileKey");
  select.innerHTML = "";
  publisherProfiles.length = 0;

  const data = await fetchJson("/user/publisher-profiles");
  if (!data.ok || !Array.isArray(data.items)) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.text = "발행 프로필 조회 실패";
    select.appendChild(opt);
    return;
  }

  if (data.items.length === 0) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.text = "등록된 publisher 프로필 없음";
    select.appendChild(opt);
    return;
  }

  data.items.forEach((item) => {
    publisherProfiles.push(item);
    const opt = document.createElement("option");
    opt.value = item.account_key || "";
    const label = item.label ? `${item.account_key} (${item.label})` : (item.account_key || "");
    opt.text = label;
    select.appendChild(opt);
  });

  applyPublisherProfileMeta();
}

function applyPublisherProfileMeta() {
  const key = document.getElementById("publisherProfileKey").value;
  const blogInput = document.getElementById("publishBlogId");
  const target = publisherProfiles.find((x) => (x.account_key || "") === key);
  if (target && target.blog_id) {
    blogInput.value = target.blog_id;
  }
}

function renderCases(results) {
  const list = document.getElementById("caseList");
  list.innerHTML = "";

  if (!Array.isArray(results) || results.length === 0) {
    list.innerText = "수집된 글이 없습니다.";
    return;
  }

  results.forEach((item, index) => {
    const div = document.createElement("div");
    div.className = "case-item";
    div.innerText = `${index + 1}. [${item.cafe_name || ""}] ${item.title || ""}`;

    div.addEventListener("click", () => {
      document.getElementById("selectedUrl").value = item.url || "";
      document.querySelectorAll(".case-item").forEach((el) => el.classList.remove("selected"));
      div.classList.add("selected");
    });

    list.appendChild(div);
  });
}

async function scrapeCases() {
  const category = document.getElementById("category").value;
  const list = document.getElementById("caseList");
  list.innerText = "수집 중...";

  const data = await fetchJson(
    `/scrape/category?category=${encodeURIComponent(category)}&limit=10`
  );

  if (data.error) {
    list.innerText = `수집 실패: ${data.error}`;
    return;
  }

  renderCases(data.results || []);
}

async function scrapgenerateBlog() {
  const ready = await ensureApiKeySetup();
  if (!ready) {
    alert("먼저 누락된 API 키를 입력해 주세요.");
    return;
  }

  const url = document.getElementById("selectedUrl").value;
  if (!url) {
    alert("먼저 피해 사례를 선택하세요.");
    return;
  }

  const payload = {
    category: document.getElementById("category").value,
    url,
    subInput: document.getElementById("subInput").value,
    subTitle: document.getElementById("subTitle").value,
    length: document.getElementById("length").value,
    provider: document.getElementById("provider").value,
    model: document.getElementById("model").value,
  };

  setResultText("글 생성 중...");

  const data = await fetchJson("/user/scrapgenerate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const resultText = data.result || JSON.stringify(data, null, 2);
  setResultText(resultText);

  // const publishTitleEl = document.getElementById("publishTitle");
  // if (!publishTitleEl.value.trim()) {
  //   const guessed = guessTitleFromGeneratedText(resultText);
  //   if (guessed) publishTitleEl.value = guessed;
  // }
}

async function keywordgenerateBlog() {
  const ready = await ensureApiKeySetup();
  if (!ready) {
    alert("먼저 누락된 API 키를 입력해 주세요.");
    return;
  }

  const keywords = document.getElementById("keywordInput").value;
  if (!keywords) {
    alert("먼저 키워드를 입력하세요.");
    return;
  }

  const subinput = document.getElementById("subInput").value;
  if (!subinput) {
    alert("키워드로 글을 생성시엔 상세 요청란을 입력하세요.");
    return;
  }

  const payload = {
    keywords: document.getElementById("keywordInput").value,
    subInput: document.getElementById("subInput").value,
    subTitle: document.getElementById("subTitle").value,
    length: document.getElementById("length").value,
    provider: document.getElementById("provider").value,
    model: document.getElementById("model").value,
  };

  setResultText("글 생성 중...");

  const data = await fetchJson("/user/keywordgenerate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const resultText = data.result || JSON.stringify(data, null, 2);
  setResultText(resultText);

  // const publishTitleEl = document.getElementById("publishTitle");
  // if (!publishTitleEl.value.trim()) {
  //   const guessed = guessTitleFromGeneratedText(resultText);
  //   if (guessed) publishTitleEl.value = guessed;
  // }
}

async function blogScrapgenerateBlog() {
  const ready = await ensureApiKeySetup();
  if (!ready) {
    alert("먼저 누락된 API 키를 입력해 주세요.");
    return;
  }

  const url = document.getElementById("blogUrlInput").value.trim();
  if (!url) {
    alert("먼저 블로그 URL을 입력하세요.");
    return;
  }

  const payload = {
    url,
    subInput: document.getElementById("subInput").value,
    subTitle: document.getElementById("subTitle").value,
    length: document.getElementById("length").value,
    provider: document.getElementById("provider").value,
    model: document.getElementById("model").value,
  };

  setResultText("글 생성 중...");

  const data = await fetchJson("/user/blogscrapgenerate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const resultText = data.result || JSON.stringify(data, null, 2);
  setResultText(resultText);
}

function toPrettyJson(value) {
  try {
    return JSON.stringify(value ?? {}, null, 2);
  } catch {
    return String(value ?? "");
  }
}

function buildVpnDebugText(data) {
  const lines = [];

  if (data?.vpn_debug) {
    lines.push(toPrettyJson(data.vpn_debug));
  }

  if (data?.disconnect_debug) {
    lines.push(toPrettyJson(data.disconnect_debug));
  }

  return lines.join("\n");
}

function clampInt(value, minVal, maxVal, defaultVal) {
  const n = Number(value);
  if (!Number.isFinite(n)) return defaultVal;
  return Math.max(minVal, Math.min(maxVal, Math.trunc(n)));
}

function toggleRandomImageOptionBox() {
  const useRandom = !!document.getElementById("publishUseRandomImage")?.checked;
  const box = document.getElementById("randomImageOptionBox");
  if (box) box.hidden = !useRandom;
}

function formatDatetimeLocal(date) {
  const pad = (n) => String(n).padStart(2, "0");
  return [
    date.getFullYear(),
    "-",
    pad(date.getMonth() + 1),
    "-",
    pad(date.getDate()),
    "T",
    pad(date.getHours()),
    ":",
    pad(date.getMinutes()),
  ].join("");
}

function getNextTenMinuteDate() {
  const d = new Date();
  d.setSeconds(0, 0);
  const remainder = d.getMinutes() % 10;
  d.setMinutes(d.getMinutes() + (remainder === 0 ? 10 : 10 - remainder));
  return d;
}

function toggleScheduleOptionBox() {
  const useSchedule = !!document.getElementById("publishUseSchedule")?.checked;
  const box = document.getElementById("scheduleOptionBox");
  const input = document.getElementById("publishScheduledAt");
  if (box) box.hidden = !useSchedule;
  if (input) input.min = formatDatetimeLocal(getNextTenMinuteDate());
}

function validateScheduledAt(value) {
  if (!value) return "예약발행 시간을 입력하세요.";

  const scheduledDate = new Date(value);
  if (Number.isNaN(scheduledDate.getTime())) {
    return "예약발행 시간 형식이 올바르지 않습니다.";
  }

  if (scheduledDate <= new Date()) {
    return "예약발행 시간은 현재보다 이후여야 합니다.";
  }

  if (
    scheduledDate.getMinutes() % 10 !== 0 ||
    scheduledDate.getSeconds() !== 0 ||
    scheduledDate.getMilliseconds() !== 0
  ) {
    return "네이버 예약발행 시간은 10분 단위로 입력하세요.";
  }

  return "";
}

function normalizeOptionalUrl(value) {
  const text = String(value || "").trim();
  if (!text) return "";
  if (/^https?:\/\//i.test(text)) return text;
  return `https://${text}`;
}

async function publishBlog() {
  const title = document.getElementById("publishTitle").value.trim();
  const publisherProfileKey = document.getElementById("publisherProfileKey").value.trim();
  const blogId = document.getElementById("publishBlogId").value.trim();
  const includeRandomImage = !!document.getElementById("publishUseRandomImage")?.checked;
  const useSchedule = !!document.getElementById("publishUseSchedule")?.checked;
  const scheduledAt = document.getElementById("publishScheduledAt")?.value || "";
  const middleImageCount = clampInt(document.getElementById("middleImageCount")?.value, 0, 10, 1);
  const bottomImageCount = clampInt(document.getElementById("bottomImageCount")?.value, 0, 10, 1);
  const bottomImageLink = normalizeOptionalUrl(document.getElementById("bottomImageLink")?.value);
  const bottomFirstImageLink = normalizeOptionalUrl(document.getElementById("bottomFirstImageLink")?.value);

  const typingDelayMin = clampInt(document.getElementById("typingDelayMin")?.value, 0, 500, 30);
  const typingDelayMax = clampInt(document.getElementById("typingDelayMax")?.value, 0, 500, 85);  

  const conclusionParagraphCount = clampInt(document.getElementById("conclusionParagraphCount")?.value, 0, 10, 1);
  const bodyFontSize = document.getElementById("bodyFontSize")?.value || "15";
  const subtitleFontSize = document.getElementById("subtitleFontSize")?.value || "24";
  const subtitleQuoteStyle = clampInt(document.getElementById("subtitleQuoteStyle")?.value, 1, 5, 1);

  const content = getResultText();
  const statusEl = document.getElementById("publishStatus");

  if (!title) {
    alert("발행 제목을 입력하세요.");
    return;
  }
  if (!publisherProfileKey) {
    alert("발행 계정 키(publisher)를 선택하세요.");
    return;
  }
  if (!content || content === "글 생성 중...") {
    alert("먼저 생성된 본문이 필요합니다.");
    return;
  }
  if (content.startsWith("에러 발생:")) {
    alert("생성 결과가 에러 상태입니다. 발행 전에 본문을 다시 생성하세요.");
    return;
  }
  if (useSchedule) {
    const scheduleError = validateScheduledAt(scheduledAt);
    if (scheduleError) {
      alert(scheduleError);
      return;
    }
  }

  statusEl.innerText = useSchedule ? "블로그 예약발행 중..." : "블로그 발행 중...";

  const data = await fetchJson("/user/publish", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title,
      content,
      publisher_profile_key: publisherProfileKey,
      blog_id: blogId,
      publish_mode: useSchedule ? "scheduled" : "now",
      scheduled_at: useSchedule ? scheduledAt : "",
      include_random_image: includeRandomImage,
      middle_image_count: includeRandomImage ? middleImageCount : 0,
      bottom_image_count: includeRandomImage ? bottomImageCount : 0,
      bottom_image_link: includeRandomImage ? bottomImageLink : "",
      bottom_first_image_link: includeRandomImage ? bottomFirstImageLink : "",
      typing_delay_min: typingDelayMin,
      typing_delay_max: typingDelayMax,
      conclusion_paragraph_count: conclusionParagraphCount,
      body_font_size: bodyFontSize,
      subtitle_font_size: subtitleFontSize,
      subtitle_quote_style: subtitleQuoteStyle,
    }),
  });

  if (!data.ok) {
    let msg = `발행 실패: ${data.message || "알 수 없는 오류"}`;
    const debugText = buildVpnDebugText(data);
    if (debugText) msg += `\n\n${debugText}`;
    statusEl.innerText = msg;
    return;
  }

  let msg = (data.publish_mode === "scheduled" || useSchedule) ? "예약발행 완료" : "발행 완료";
  if (data.scheduled_at) msg += `\n예약 시간: ${data.scheduled_at}`;
  if (data.url) msg += `\nURL: ${data.url}`;
  if (data.disconnect_warning) msg += `\n\ndisconnect warning: ${data.disconnect_warning}`;

  const debugText = buildVpnDebugText(data);
  if (debugText) msg += `\n\n${debugText}`;

  statusEl.innerText = msg;
}

function cleanGeneratedTitle(raw) {
  let t = String(raw || "").trim();
  if (!t) return "";

  // 코드블록/따옴표/마크다운 제목 기호 제거
  t = t.replace(/^```[\s\S]*?\n/, "").replace(/```$/, "").trim();
  t = t.replace(/^#+\s*/, "").trim();
  t = t.replace(/^["'“”‘’\[\(]+/, "").replace(/["'“”‘’\]\)]+$/, "").trim();

  // 여러 줄이면 첫 줄만 사용
  t = t.split("\n").map((x) => x.trim()).filter(Boolean)[0] || "";
  return t.slice(0, 120).trim();
}

async function generateTitleFromBody() {
  const ready = await ensureApiKeySetup();
  if (!ready) {
    alert("먼저 API 키를 입력해 주세요.");
    return;
  }

  const caseText = getResultText();
  if (!caseText || caseText === "글 생성 중..") {
    alert("제목 생성 전에 본문(결과 텍스트)을 먼저 준비해 주세요.");
    return;
  }

  const statusEl = document.getElementById("publishStatus");
  if (statusEl) statusEl.innerText = "제목 생성 중..";

  const payload = {
    case: caseText,
    subInput2: document.getElementById("subInput2").value || "",
    provider: document.getElementById("provider").value,
    model: document.getElementById("model").value,
  };

  const data = await fetchJson("/user/titlegenerate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const rawTitle = data.result || "";
  if (rawTitle.startsWith("에러 발생:")) {
    if (statusEl) statusEl.innerText = rawTitle;
    return;
  }

  const title = cleanGeneratedTitle(rawTitle);
  if (!title) {
    if (statusEl) statusEl.innerText = "제목 생성 실패: AI 응답에서 제목을 추출하지 못했습니다.";
    return;
  }

  document.getElementById("publishTitle").value = title;
  if (statusEl) statusEl.innerText = "제목 생성 완료";
}

async function loadTitlePrompt_setting() {
  const res = await fetch("/user/titleprompt/get");

  const data = await res.json();
  if (!data.ok) {
    alert(data.message || "프롬프트 로드 실패");
    return;
  }
  document.getElementById("titlegenaratorprompt_setting").value = data.title_prompt || "";
}

async function savetitlegenaratorPrompt_setting() {
  const prompt = document.getElementById("titlegenaratorprompt_setting").value;
  const res = await fetch("/user/titlesave-prompt", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title_prompt: prompt }),
  });

  const data = await res.json();
  if (!data.ok) {
    alert(data.message || "프롬프트 저장 실패");
    return;
  }
  alert("프롬프트 저장 완료");
}

async function toggleTitlePrompt_setting() {
  const wrapper = document.getElementById("publishSettingsWrapper");
  const promptArea = document.getElementById("titlegenaratorprompt_setting");
  const saveBtn = document.getElementById("savetitlegenaratorPrompt_settingBtn");
  const toggleBtn = document.getElementById("titlegenaratorprompt_settingBtn");
  const titlebr = document.getElementById("titlebr");

  if (!wrapper || !promptArea || !saveBtn || !toggleBtn) return;

  isTitlePromptSettingOpen = !isTitlePromptSettingOpen;

  if (isTitlePromptSettingOpen) {
    wrapper.hidden = true;
    titlebr.hidden = false;
    promptArea.hidden = false;
    saveBtn.hidden = false;
    toggleBtn.innerText = "프롬프트 설정 닫기";

    return;
  }

  titlebr.hidden = true;
  promptArea.hidden = true;
  saveBtn.hidden = true;
  wrapper.hidden = false;
  toggleBtn.innerText = "제목 생성 프롬프트 설정";
}

async function init() {
  document.getElementById("saveApiKeysBtn").addEventListener("click", saveApiKeys);
  document.getElementById("scrapeBtn").addEventListener("click", scrapeCases);
  document.getElementById("scrapgenerateBtn").addEventListener("click", scrapgenerateBlog);
  document.getElementById("keywordgenerateBtn").addEventListener("click", keywordgenerateBlog);
  document.getElementById("blogScrapgenerateBtn").addEventListener("click", blogScrapgenerateBlog);
  document.getElementById("publishBtn").addEventListener("click", publishBlog);
  document.getElementById("provider").addEventListener("change", loadModelsByProvider);
  document.getElementById("publisherProfileKey").addEventListener("change", applyPublisherProfileMeta);
  document.getElementById("modeScrapeBtn").addEventListener("click", () => setGenerateMode(MODE_SCRAPE));
  document.getElementById("modeKeywordBtn").addEventListener("click", () => setGenerateMode(MODE_KEYWORD));
  document.getElementById("modeBlogScrapeBtn").addEventListener("click", () => setGenerateMode(MODE_BLOG_SCRAPE));
  document.getElementById("publishUseRandomImage")?.addEventListener("change", toggleRandomImageOptionBox);
  document.getElementById("publishUseSchedule")?.addEventListener("change", toggleScheduleOptionBox);
  document.getElementById("generateTitleBtn").addEventListener("click", generateTitleFromBody);

  document.getElementById("titlegenaratorprompt_settingBtn").addEventListener("click", toggleTitlePrompt_setting);
  document.getElementById("savetitlegenaratorPrompt_settingBtn").addEventListener("click", savetitlegenaratorPrompt_setting);

  await loadCategories();
  await ensureApiKeySetup();
  await loadModelsByProvider();
  await loadPublisherProfiles();
  await loadTitlePrompt_setting();

  setGenerateMode(MODE_SCRAPE);
  toggleRandomImageOptionBox();
  toggleScheduleOptionBox();
}

window.addEventListener("DOMContentLoaded", init);
