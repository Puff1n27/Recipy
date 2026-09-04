// ── API URLS ──────────────────────────────────────────
const API      = "/api/expenses";
const AUTH_API = "/api/auth";

// ── STATE ─────────────────────────────────────────────
let allExpenses  = [];
let currentUser  = null;
let cameraStream = null;

// ══════════════════════════════════════════════════════
// AUTH FUNCTIONS
// ══════════════════════════════════════════════════════

// Switch between Login and Register tabs
function showAuthTab(tab) {
  document.querySelectorAll(".auth-tab").forEach(t => t.classList.remove("active"));
  document.querySelectorAll(".auth-form").forEach(f => f.style.display = "none");

  document.querySelector(`.auth-tab:${tab === "login" ? "first" : "last"}-child`)
    .classList.add("active");
  document.getElementById(`${tab}-form`).style.display = "flex";

  // Clear errors
  document.getElementById("login-error").textContent    = "";
  document.getElementById("register-error").textContent = "";
}

// Register new account
async function register() {
  const username = document.getElementById("reg-username").value.trim();
  const email    = document.getElementById("reg-email").value.trim();
  const password = document.getElementById("reg-password").value.trim();
  const errorEl  = document.getElementById("register-error");

  if (!username || !email || !password) {
    errorEl.textContent = "Please fill in all fields";
    return;
  }

  if (password.length < 6) {
    errorEl.textContent = "Password must be at least 6 characters";
    return;
  }

  try {
    const res  = await fetch(`${AUTH_API}/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, email, password })
    });

    const data = await res.json();

    if (!res.ok) {
      errorEl.textContent = data.error || "Registration failed";
      return;
    }

    // Success — enter app
    enterApp(data.user);
    showToast(`Welcome to ReciPy, ${data.user.username}! 🎉`, "success");

  } catch (err) {
    errorEl.textContent = "Connection error — is Flask running?";
  }
}

// Login
async function login() {
  const email    = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value.trim();
  const errorEl  = document.getElementById("login-error");

  if (!email || !password) {
    errorEl.textContent = "Please enter email and password";
    return;
  }

  try {
    const res  = await fetch(`${AUTH_API}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });

    const data = await res.json();

    if (!res.ok) {
      errorEl.textContent = data.error || "Login failed";
      return;
    }

    enterApp(data.user);
    showToast(`Welcome back, ${data.user.username}! 👋`, "success");

  } catch (err) {
    errorEl.textContent = "Connection error — is Flask running?";
  }
}

// Logout
async function logout() {
  try {
    await fetch(`${AUTH_API}/logout`, { method: "POST" });
  } catch (err) {}

  currentUser = null;
  document.getElementById("app-screen").style.display  = "none";
  document.getElementById("auth-screen").style.display = "flex";
  showToast("Logged out successfully", "success");
}

// Enter app after login/register
function enterApp(user) {
  currentUser = user;

  // Update UI with user info
  document.getElementById("user-name").textContent  = user.username;
  document.getElementById("user-email").textContent = user.email;
  document.getElementById("user-avatar").textContent = user.username[0].toUpperCase();
  document.getElementById("welcome-msg").textContent = `👋 Hi, ${user.username}!`;

  // Show app, hide auth
  document.getElementById("auth-screen").style.display = "none";
  document.getElementById("app-screen").style.display  = "block";

  loadDashboard();
}

// Check if already logged in on page load
async function checkAuth() {
  try {
    const res  = await fetch(`${AUTH_API}/status`);
    const data = await res.json();

    if (data.logged_in) {
      enterApp(data.user);
    }
  } catch (err) {
    // Not logged in — show auth screen
  }
}

// ══════════════════════════════════════════════════════
// NAVIGATION
// ══════════════════════════════════════════════════════

function showPage(page) {
  document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));

  document.getElementById(`page-${page}`).classList.add("active");

  const pages    = ["dashboard", "scan", "expenses", "add"];
  const navItems = document.querySelectorAll(".nav-item");
  navItems[pages.indexOf(page)]?.classList.add("active");

  if (page === "dashboard") loadDashboard();
  if (page === "expenses")  loadExpenses();
}

// ══════════════════════════════════════════════════════
// DASHBOARD
// ══════════════════════════════════════════════════════

async function loadDashboard() {
  try {
    const res  = await fetch(`${API}/stats`);

    if (res.status === 401) { logout(); return; }

    const data = await res.json();

    document.getElementById("stat-month").textContent = `¥${fmt(data.total_this_month)}`;
    document.getElementById("stat-year").textContent  = `¥${fmt(data.total_this_year)}`;
    document.getElementById("stat-count").textContent = data.expense_count;
    document.getElementById("stat-avg").textContent   = `¥${fmt(data.average_per_day)}`;

    renderBarChart(data.monthly_chart || []);
    renderCategoryChart(data.category_breakdown || []);
    loadRecent();

  } catch (err) {
    console.error("Dashboard error:", err);
  }
}

function renderBarChart(data) {
  const el = document.getElementById("monthly-chart");
  if (!data.length) {
    el.innerHTML = '<p class="empty-chart">No data yet — add your first expense!</p>';
    return;
  }

  const max = Math.max(...data.map(d => d.total));
  el.innerHTML = data.map(d => `
    <div class="bar-item">
      <div class="bar" style="height:${Math.max((d.total/max*90)+10, 4)}px"
           title="¥${fmt(d.total)}"></div>
      <div class="bar-label">${d.month.slice(5)}</div>
    </div>
  `).join("");
}

function renderCategoryChart(data) {
  const el = document.getElementById("category-chart");
  if (!data.length) {
    el.innerHTML = '<p class="empty-chart">No categories yet</p>';
    return;
  }

  const colors = {
    food: "#FBBF24", transport: "#38BDF8",
    shopping: "#818CF8", health: "#34D399",
    entertainment: "#FB923C", other: "#64748B"
  };

  const max = Math.max(...data.map(d => d.total));
  el.innerHTML = data.slice(0,5).map(d => `
    <div class="cat-row">
      <div class="cat-dot" style="background:${colors[d.category]||'#64748B'}"></div>
      <div class="cat-name">${d.category || "other"}</div>
      <div class="cat-track">
        <div class="cat-fill" style="width:${(d.total/max*100)}%;background:${colors[d.category]||'#64748B'}"></div>
      </div>
      <div class="cat-amt">¥${fmt(d.total)}</div>
    </div>
  `).join("");
}

async function loadRecent() {
  try {
    const res  = await fetch(`${API}/?limit=5`);
    const data = await res.json();
    const el   = document.getElementById("recent-list");

    if (!data.length) {
      el.innerHTML = `
        <div class="empty-state" style="padding:24px 0">
          <div class="empty-icon">🧾</div>
          <p>No expenses yet — scan a receipt to start!</p>
        </div>`;
      return;
    }

    el.innerHTML = data.map(e => `
      <div class="recent-item">
        <div>
          <div class="recent-shop">${e.shop_name || "Unknown"}</div>
          <div class="recent-date">${e.date || "—"} · ${e.category || "—"}</div>
        </div>
        <div class="recent-amount">¥${fmt(e.total_amount || 0)}</div>
      </div>
    `).join("");

  } catch (err) {
    console.error("Recent error:", err);
  }
}

// ══════════════════════════════════════════════════════
// EXPENSES LIST
// ══════════════════════════════════════════════════════

async function loadExpenses() {
  try {
    const res = await fetch(`${API}/`);
    if (res.status === 401) { logout(); return; }

    allExpenses = await res.json();
    renderExpenses(allExpenses);

    document.getElementById("expense-count-label").textContent =
      `${allExpenses.length} expense${allExpenses.length !== 1 ? "s" : ""} total`;

  } catch (err) {
    console.error("Expenses error:", err);
  }
}

function renderExpenses(list) {
  const tbody = document.getElementById("expense-tbody");

  if (!list.length) {
    tbody.innerHTML = `
      <tr><td colspan="5">
        <div class="empty-state">
          <div class="empty-icon">🧾</div>
          <p>No expenses found</p>
        </div>
      </td></tr>`;
    return;
  }

  tbody.innerHTML = list.map(e => `
    <tr>
      <td>${e.date || "—"}</td>
      <td><strong>${e.shop_name || "Unknown"}</strong></td>
      <td><span class="tag tag-${e.category||'other'}">${e.category || "other"}</span></td>
      <td class="amount-cell">¥${fmt(e.total_amount || 0)}</td>
      <td>
        <button class="btn btn-danger btn-sm" onclick="deleteExpense(${e.id})">
          Delete
        </button>
      </td>
    </tr>
  `).join("");
}

function filterBy(cat, btn) {
  document.querySelectorAll(".filter").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
  const filtered = cat === "all"
    ? allExpenses
    : allExpenses.filter(e => e.category === cat);
  renderExpenses(filtered);
}

async function deleteExpense(expense_id) {
  if (!confirm("Delete this expense?")) return;

  try {
    const res = await fetch(`${API}/${expense_id}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Delete failed");

    showToast("Deleted! ✓", "success");
    loadExpenses();
    loadDashboard();
  } catch (err) {
    showToast("Error deleting", "error");
  }
}

// ══════════════════════════════════════════════════════
// ADD EXPENSE MANUALLY
// ══════════════════════════════════════════════════════

async function addExpense() {
  const expense = {
    shop_name:    document.getElementById("add-shop").value,
    date:         document.getElementById("add-date").value,
    total_amount: parseFloat(document.getElementById("add-amount").value) || null,
    category:     document.getElementById("add-category").value,
    notes:        document.getElementById("add-notes").value
  };

  if (!expense.shop_name && !expense.total_amount) {
    showToast("Please fill in shop name and amount", "error");
    return;
  }

  try {
    const res = await fetch(`${API}/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(expense)
    });

    if (res.status === 401) { logout(); return; }
    if (!res.ok) throw new Error("Save failed");

    showToast("Expense saved! 💾", "success");
    clearAddForm();
    setTimeout(() => showPage("expenses"), 1000);

  } catch (err) {
    showToast("Error saving expense", "error");
  }
}

function clearAddForm() {
  ["add-shop","add-date","add-amount","add-notes"].forEach(id => {
    document.getElementById(id).value = "";
  });
  document.getElementById("add-category").value = "";
}

// ══════════════════════════════════════════════════════
// CAMERA
// ══════════════════════════════════════════════════════

async function startCamera() {
  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment" }
    });
    const video = document.getElementById("cameraVideo");
    video.srcObject = cameraStream;
    document.getElementById("cameraBox").classList.add("active");
    document.getElementById("cameraControls").style.display = "flex";
    document.getElementById("uploadZone").style.display     = "none";
  } catch (err) {
    showToast("Camera not available on this device", "error");
  }
}

function capturePhoto() {
  const video  = document.getElementById("cameraVideo");
  const canvas = document.getElementById("cameraCanvas");
  canvas.width  = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext("2d").drawImage(video, 0, 0);

  canvas.toBlob(blob => {
    const file = new File([blob], "capture.jpg", { type: "image/jpeg" });
    showPreview(file);
    stopCamera();
  }, "image/jpeg", 0.95);
}

function stopCamera() {
  if (cameraStream) {
    cameraStream.getTracks().forEach(t => t.stop());
    cameraStream = null;
  }
  document.getElementById("cameraBox").classList.remove("active");
  document.getElementById("cameraControls").style.display = "none";
  document.getElementById("uploadZone").style.display     = "block";
}

// ══════════════════════════════════════════════════════
// FILE UPLOAD & SCAN
// ══════════════════════════════════════════════════════

function handleFile(event) {
  const file = event.target.files[0];
  if (file) showPreview(file);
}

function showPreview(file) {
  window._selectedFile = file;
  const reader = new FileReader();
  reader.onload = e => {
    document.getElementById("previewImg").src          = e.target.result;
    document.getElementById("previewBox").style.display   = "block";
    document.getElementById("uploadZone").style.display   = "none";
    document.getElementById("result-empty").style.display = "block";
    document.getElementById("result-form").style.display  = "none";
  };
  reader.readAsDataURL(file);
}

async function scanReceipt() {
  if (!window._selectedFile) {
    showToast("No file selected", "error");
    return;
  }

  document.getElementById("previewBox").style.display   = "none";
  document.getElementById("scanningAnim").style.display = "block";

  const formData = new FormData();
  formData.append("file", window._selectedFile);

  try {
    const res  = await fetch("/api/scan", { method: "POST", body: formData });
    const data = await res.json();

    document.getElementById("scanningAnim").style.display = "none";

    if (!res.ok) {
      showToast(data.error || "Scan failed", "error");
      document.getElementById("previewBox").style.display = "block";
      return;
    }

    showResult(data);
    showToast("Receipt scanned! ✅", "success");

  } catch (err) {
    document.getElementById("scanningAnim").style.display = "none";
    document.getElementById("previewBox").style.display   = "block";
    showToast("Scan failed — check backend", "error");
  }
}

function showResult(data) {
  document.getElementById("result-empty").style.display = "none";
  document.getElementById("result-form").style.display  = "block";

  document.getElementById("field-shop").value   = data.shop_name    || "";
  document.getElementById("field-date").value   = data.date         || "";
  document.getElementById("field-amount").value = data.total_amount || "";
  document.getElementById("field-raw").value    = data.raw_text     || "";
}

async function saveScannedExpense() {
  const expense = {
    shop_name:    document.getElementById("field-shop").value,
    date:         document.getElementById("field-date").value,
    total_amount: parseFloat(document.getElementById("field-amount").value) || null,
    category:     document.getElementById("field-category").value,
    notes:        document.getElementById("field-notes").value
  };

  try {
    const res = await fetch(`${API}/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(expense)
    });

    if (res.status === 401) { logout(); return; }
    if (!res.ok) throw new Error("Save failed");

    showToast("Expense saved! 💾", "success");
    resetScan();
    setTimeout(() => showPage("expenses"), 1000);

  } catch (err) {
    showToast("Error saving", "error");
  }
}

function resetScan() {
  window._selectedFile = null;
  document.getElementById("fileInput").value            = "";
  document.getElementById("previewBox").style.display   = "none";
  document.getElementById("uploadZone").style.display   = "block";
  document.getElementById("scanningAnim").style.display = "none";
  document.getElementById("result-empty").style.display = "block";
  document.getElementById("result-form").style.display  = "none";
  ["field-shop","field-date","field-amount","field-notes","field-raw"].forEach(id => {
    document.getElementById(id).value = "";
  });
  document.getElementById("field-category").value = "";
}

// ── DRAG AND DROP ─────────────────────────────────────
const uploadZone = document.getElementById("uploadZone");

uploadZone.addEventListener("dragover", e => {
  e.preventDefault();
  uploadZone.style.borderColor = "var(--blue)";
});

uploadZone.addEventListener("dragleave", () => {
  uploadZone.style.borderColor = "rgba(56,189,248,0.3)";
});

uploadZone.addEventListener("drop", e => {
  e.preventDefault();
  uploadZone.style.borderColor = "rgba(56,189,248,0.3)";
  const file = e.dataTransfer.files[0];
  if (file) showPreview(file);
});

// ── ENTER KEY SUPPORT ─────────────────────────────────
document.getElementById("login-password").addEventListener("keydown", e => {
  if (e.key === "Enter") login();
});

document.getElementById("reg-password").addEventListener("keydown", e => {
  if (e.key === "Enter") register();
});

// ══════════════════════════════════════════════════════
// HELPERS
// ══════════════════════════════════════════════════════

function fmt(num) {
  return Math.round(num || 0).toLocaleString("ja-JP");
}

function showToast(msg, type = "success") {
  const toast = document.getElementById("toast");
  toast.textContent = msg;
  toast.className   = `toast ${type} show`;
  setTimeout(() => toast.classList.remove("show"), 3000);
}

// ══════════════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════════════

document.getElementById("current-date").textContent =
  new Date().toLocaleDateString("en-US", {
    weekday: "long", year: "numeric",
    month: "long",  day: "numeric"
  });

// Check if already logged in
checkAuth();