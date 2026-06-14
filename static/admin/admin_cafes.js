function authExpired(status) {
  if (status === 401) {
    alert("로그인이 필요합니다.");
    location.href = "/admin/login";
    return true;
  }
  return false;
}

function onFilterTypeChange() {
  const ft = document.getElementById("filter_type").value;
  document.getElementById("keywordRow").style.display = ft === "keyword" ? "block" : "none";
}

function onMemberRequiredChange() {
  const checked = document.getElementById("member_required").checked;
  document.getElementById("accountKeyRow").style.display = checked ? "block" : "none";
}

function resetForm() {
  document.getElementById("cafeId").value = "";
  document.getElementById("category").value = "";
  document.getElementById("name").value = "";
  document.getElementById("url").value = "";
  document.getElementById("filter_type").value = "keyword";
  document.getElementById("keyword").value = "";
  document.getElementById("member_required").checked = false;
  document.getElementById("scraper_profile_key").value = "";
  onFilterTypeChange();
  onMemberRequiredChange();
}

function appendTextCell(row, value) {
  const td = document.createElement("td");
  td.textContent = value ?? "";
  row.appendChild(td);
  return td;
}

function fillForm(item) {
  document.getElementById("cafeId").value = item.id || "";
  document.getElementById("category").value = item.category || "";
  document.getElementById("name").value = item.name || "";
  document.getElementById("url").value = item.url || "";
  document.getElementById("filter_type").value = item.filter_type || "keyword";
  document.getElementById("keyword").value = item.keyword || "";
  document.getElementById("member_required").checked = !!item.member_required;
  document.getElementById("scraper_profile_key").value = item.scraper_profile_key || item.naver_account_key || "";
  onFilterTypeChange();
  onMemberRequiredChange();
}

async function loadCafes() {
  const res = await fetch("/admin/cafes/list");
  if (authExpired(res.status)) return;

  const data = await res.json();
  if (!data.ok) {
    alert(data.message || "목록 조회 실패");
    return;
  }

  const tbody = document.getElementById("rows");
  tbody.innerHTML = "";

  (data.items || []).forEach((item, idx) => {
    const tr = document.createElement("tr");
    appendTextCell(tr, idx + 1);
    appendTextCell(tr, item.category || "");
    appendTextCell(tr, item.name || "");
    appendTextCell(tr, item.url || "");
    appendTextCell(tr, item.filter_type || "");
    appendTextCell(tr, item.keyword || "");
    appendTextCell(tr, item.member_required ? "Y" : "N");
    appendTextCell(tr, item.scraper_profile_key || item.naver_account_key || "");

    const manageTd = document.createElement("td");

    const editBtn = document.createElement("button");
    editBtn.type = "button";
    editBtn.innerText = "수정";
    editBtn.className = "table-edit-btn";
    editBtn.onclick = () => fillForm(item);

    const delBtn = document.createElement("button");
    delBtn.type = "button";
    delBtn.innerText = "삭제";
    delBtn.className = "table-delete-btn";
    delBtn.style.marginLeft = "6px";
    delBtn.onclick = () => removeCafe(item.id);

    manageTd.appendChild(editBtn);
    manageTd.appendChild(delBtn);
    tr.appendChild(manageTd);
    tbody.appendChild(tr);
  });
}

async function saveCafe() {
  const cafeId = document.getElementById("cafeId").value.trim();
  const payload = {
    category: document.getElementById("category").value.trim(),
    name: document.getElementById("name").value.trim(),
    url: document.getElementById("url").value.trim(),
    filter_type: document.getElementById("filter_type").value,
    keyword: document.getElementById("keyword").value.trim(),
    member_required: document.getElementById("member_required").checked,
    scraper_profile_key: document.getElementById("scraper_profile_key").value.trim(),
  };

  const endpoint = cafeId ? `/admin/cafes/${encodeURIComponent(cafeId)}` : "/admin/cafes/create";
  const method = cafeId ? "PUT" : "POST";

  const res = await fetch(endpoint, {
    method,
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });

  if (authExpired(res.status)) return;
  const data = await res.json();

  if (!data.ok) {
    alert(data.message || "저장 실패");
    return;
  }

  alert("저장 완료");
  resetForm();
  await loadCafes();
}

async function removeCafe(cafeId) {
  if (!cafeId) {
    alert("삭제할 카페 ID가 없습니다.");
    return;
  }
  if (!confirm("삭제하시겠습니까?")) return;

  const res = await fetch(`/admin/cafes/${encodeURIComponent(cafeId)}`, { method: "DELETE" });
  if (authExpired(res.status)) return;

  const data = await res.json();
  if (!data.ok) {
    alert(data.message || "삭제 실패");
    return;
  }

  alert("삭제 완료");
  await loadCafes();
}

window.addEventListener("DOMContentLoaded", async () => {
  document.getElementById("filter_type").addEventListener("change", onFilterTypeChange);
  document.getElementById("member_required").addEventListener("change", onMemberRequiredChange);
  document.getElementById("saveBtn").addEventListener("click", saveCafe);
  document.getElementById("resetBtn").addEventListener("click", resetForm);

  onFilterTypeChange();
  onMemberRequiredChange();
  await loadCafes();
});
