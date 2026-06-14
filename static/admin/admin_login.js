async function login() {
  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value.trim();

  const res = await fetch("/admin/login", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ username, password }),
  });

  const data = await res.json();
  if (!data.ok) {
    alert(data.message || "로그인 실패");
    return;
  }

  location.href = "/admin";
}

window.addEventListener("DOMContentLoaded", () => {
  document.getElementById("loginBtn").addEventListener("click", login);
});
