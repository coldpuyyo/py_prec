function getProfileKey() {
  return document.getElementById("profileKey").value.trim();
}

function getProfileRole() {
  return document.getElementById("profileRole").value;
}

function setProfileStatus(text) {
  document.getElementById("profileStatus").innerText = text;
}

function appendTextCell(row, value) {
  const td = document.createElement("td");
  td.textContent = value ?? "";
  row.appendChild(td);
  return td;
}

async function readJsonResponse(res) {
  try {
    return await res.json();
  } catch {
    return { ok: false, message: `응답을 읽을 수 없습니다. status=${res.status}` };
  }
}

async function startProfileSetup() {
  const account_key = getProfileKey();
  if (!account_key) {
    alert("네이버 계정 키를 입력하세요.");
    return;
  }

  const res = await fetch("/user/naver-profile/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      account_key,
      role: getProfileRole(),
    }),
  });

  const data = await readJsonResponse(res);
  setProfileStatus(JSON.stringify(data, null, 2));
  if (!data.ok) alert(data.message || "시작 실패");
}

async function checkProfileSetup() {
  const account_key = getProfileKey();
  if (!account_key) {
    alert("네이버 계정 키를 입력하세요.");
    return;
  }

  const res = await fetch(
    `/user/naver-profile/status?account_key=${encodeURIComponent(account_key)}&role=${encodeURIComponent(getProfileRole())}`
  );
  const data = await readJsonResponse(res);
  setProfileStatus(JSON.stringify(data, null, 2));
}

async function finishProfileSetup() {
  const account_key = getProfileKey();
  if (!account_key) {
    alert("네이버 계정 키를 입력하세요.");
    return;
  }

  const res = await fetch("/user/naver-profile/finish", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      account_key,
      role: getProfileRole(),
    }),
  });

  const data = await readJsonResponse(res);
  setProfileStatus(JSON.stringify(data, null, 2));
  if (data.ok && !data.logged_in) {
    alert("로그인 쿠키가 확인되지 않았습니다. 다시 진행해주세요.");
  }
}

async function cancelProfileSetup() {
  const account_key = getProfileKey();
  if (!account_key) {
    alert("네이버 계정 키를 입력하세요.");
    return;
  }

  const res = await fetch("/user/naver-profile/cancel", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      account_key,
      role: getProfileRole(),
    }),
  });

  const data = await readJsonResponse(res);
  setProfileStatus(JSON.stringify(data, null, 2));
}

async function loadProfileRegistry() {
  const res = await fetch("/user/naver-profiles/list");
  const data = await readJsonResponse(res);
  if (!data.ok) {
    alert(data.message || "프로필 목록 조회 실패");
    return;
  }

  const tbody = document.getElementById("registryRows");
  tbody.innerHTML = "";

  (data.items || []).forEach((item) => {
    const tr = document.createElement("tr");
    appendTextCell(tr, item.account_key || "");
    appendTextCell(tr, item.role || "");
    appendTextCell(tr, item.label || "");
    appendTextCell(tr, item.blog_id || "");
    appendTextCell(tr, item.login_id || "");
    appendTextCell(tr, item.has_login_password ? "Y" : "N");
    appendTextCell(tr, item.active ? "Y" : "N");

    const manageTd = document.createElement("td");
    const useBtn = document.createElement("button");
    useBtn.type = "button";
    useBtn.innerText = "설정값 채우기";
    useBtn.onclick = () => {
      document.getElementById("registryAccountKey").value = item.account_key || "";
      document.getElementById("registryRole").value = item.role || "scraper";
      document.getElementById("registryLabel").value = item.label || "";
      document.getElementById("registryBlogId").value = item.blog_id || "";
      document.getElementById("registryLoginId").value = item.login_id || "";
      document.getElementById("registryLoginPassword").value = "";
      document.getElementById("registryActive").checked = !!item.active;

      document.getElementById("profileKey").value = item.account_key || "";
      document.getElementById("profileRole").value = item.role || "scraper";
    };

    const delBtn = document.createElement("button");
    delBtn.type = "button";
    delBtn.innerText = "삭제";
    delBtn.className = "danger-btn";
    delBtn.onclick = () => removeProfileRegistry(item.account_key || "");

    manageTd.appendChild(useBtn);
    manageTd.appendChild(delBtn);
    tr.appendChild(manageTd);
    tbody.appendChild(tr);
  });
}

async function saveProfileRegistry() {
  const account_key = document.getElementById("registryAccountKey").value.trim();
  const role = document.getElementById("registryRole").value;
  const label = document.getElementById("registryLabel").value.trim();
  const blog_id = document.getElementById("registryBlogId").value.trim();
  const login_id = document.getElementById("registryLoginId").value.trim();
  const login_password = document.getElementById("registryLoginPassword").value.trim();
  const active = document.getElementById("registryActive").checked;

  if (!account_key) {
    alert("계정 키를 입력하세요.");
    return;
  }

  const res = await fetch("/user/naver-profiles/upsert", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      account_key,
      role,
      label,
      blog_id,
      login_id,
      login_password,
      active,
    }),
  });

  const data = await readJsonResponse(res);
  if (!data.ok) {
    alert(data.message || "프로필 저장 실패");
    return;
  }

  document.getElementById("registryLoginPassword").value = "";
  alert("프로필 저장 완료");
  await loadProfileRegistry();
}

async function removeProfileRegistry(accountKey) {
  if (!accountKey) {
    alert("삭제할 계정 키가 없습니다.");
    return;
  }
  if (!confirm(`프로필(${accountKey})을 삭제하시겠습니까?`)) return;

  const res = await fetch(`/user/naver-profiles/${encodeURIComponent(accountKey)}`, {
    method: "DELETE",
  });
  const data = await readJsonResponse(res);
  if (!data.ok) {
    alert(data.message || "프로필 삭제 실패");
    return;
  }

  alert("프로필 삭제 완료");
  await loadProfileRegistry();
}

window.addEventListener("DOMContentLoaded", async () => {
  document.getElementById("startProfileBtn").addEventListener("click", startProfileSetup);
  document.getElementById("checkProfileBtn").addEventListener("click", checkProfileSetup);
  document.getElementById("finishProfileBtn").addEventListener("click", finishProfileSetup);
  document.getElementById("cancelProfileBtn").addEventListener("click", cancelProfileSetup);
  document.getElementById("saveRegistryBtn").addEventListener("click", saveProfileRegistry);
  document.getElementById("loadRegistryBtn").addEventListener("click", loadProfileRegistry);

  await loadProfileRegistry();
});
