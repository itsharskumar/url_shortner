function getToken() {
    const token = localStorage.getItem("access_token");
    if (!token) {
        return null;
    }

    if (isTokenExpired(token)) {
        localStorage.removeItem("access_token");
        return null;
    }

    return token;
}

function parseJwtPayload(token) {
    try {
        const payload = token.split(".")[1]
            .replace(/-/g, "+")
            .replace(/_/g, "/");
        return JSON.parse(atob(payload));
    } catch (_error) {
        return null;
    }
}

function isTokenExpired(token) {
    const payload = parseJwtPayload(token);
    if (!payload || !payload.exp) {
        return true;
    }
    return Date.now() >= payload.exp * 1000;
}

function clearSessionAndRedirect(message = null) {
    localStorage.removeItem("access_token");
    if (message) {
        const currentPath = window.location.pathname;
        if (currentPath === "/auth") {
            setResult("auth-result", message, true);
            return;
        }
        const target = `/auth?msg=${encodeURIComponent(message)}`;
        window.location.href = target;
        return;
    }
    window.location.href = "/auth";
}

function setResult(id, message, isError = false) {
    const target = document.getElementById(id);
    if (!target) {
        return;
    }
    target.classList.remove("hidden");
    target.style.borderColor = isError ? "#fca5a5" : "#b8e5de";
    target.style.background = isError ? "#fff1f2" : "#ebfffc";
    target.textContent = message;
}

async function authorizedFetch(url, options = {}) {
    const token = getToken();
    if (!token) {
        throw new Error("Session expired or missing. Please login again.");
    }

    const headers = {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
        ...(options.headers || {}),
    };

    const response = await fetch(url, { ...options, headers });
    if (response.status === 401) {
        clearSessionAndRedirect("Session expired. Please login again.");
        throw new Error("Session expired. Please login again.");
    }
    return response;
}

async function registerUser(event) {
    event.preventDefault();
    const email = document.getElementById("register-email")?.value?.trim();
    const password = document.getElementById("register-password")?.value;

    try {
        const response = await fetch("/auth/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password }),
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || "Registration failed");
        }
        setResult("auth-result", data.message);
    } catch (error) {
        setResult("auth-result", error.message, true);
    }
}

async function loginUser(event) {
    event.preventDefault();
    const email = document.getElementById("login-email")?.value?.trim();
    const password = document.getElementById("login-password")?.value;

    try {
        const response = await fetch("/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password }),
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || "Login failed");
        }

        localStorage.setItem("access_token", data.access_token);
        setResult("auth-result", "Login successful. Redirecting to dashboard...");
        setTimeout(() => {
            window.location.href = "/dashboard";
        }, 700);
    } catch (error) {
        setResult("auth-result", error.message, true);
    }
}

async function shortenUrl(event) {
    event.preventDefault();

    const input = document.getElementById("original-url");
    const customCodeInput = document.getElementById("custom-code");
    const expiresInput = document.getElementById("expires-at");
    const result = document.getElementById("result");

    if (!input || !result) {
        return;
    }

    const originalUrl = input.value.trim();
    const customCode = customCodeInput?.value?.trim() || null;
    const expiresAt = expiresInput?.value || null;

    if (!originalUrl) {
        return;
    }

    try {
        const response = await authorizedFetch("/shorten", {
            method: "POST",
            body: JSON.stringify({
                original_url: originalUrl,
                custom_code: customCode,
                expires_at: expiresAt,
            }),
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || "Failed to shorten URL");
        }

        result.classList.remove("hidden");
        result.innerHTML = `
            <strong>Short URL:</strong>
            <a href="${data.short_url}" target="_blank" rel="noreferrer">${data.short_url}</a>
        `;
        input.value = "";
        if (customCodeInput) {
            customCodeInput.value = "";
        }
        if (expiresInput) {
            expiresInput.value = "";
        }
    } catch (error) {
        setResult("result", error.message, true);
    }
}

function renderAnalytics(data) {
    const analytics = document.getElementById("analytics");
    if (!analytics) {
        return;
    }

    const topList = data.top_urls
        .map(
            (u) =>
                `<li><strong>${u.short_code}</strong> - ${u.clicks} clicks</li>`
        )
        .join("");
    const perDayList = data.links_per_day
        .map((d) => `<li>${d.day}: ${d.links_created}</li>`)
        .join("");

    analytics.innerHTML = `
        <div class="analytics-card">
            <h3>Total URLs</h3>
            <p>${data.totals.total_urls}</p>
        </div>
        <div class="analytics-card">
            <h3>Total Clicks</h3>
            <p>${data.totals.total_clicks}</p>
        </div>
        <div class="analytics-card">
            <h3>Top 5 URLs</h3>
            <ol class="muted">${topList || "<li>No data</li>"}</ol>
        </div>
        <div class="analytics-card">
            <h3>Links Per Day</h3>
            <ul class="muted">${perDayList || "<li>No data</li>"}</ul>
        </div>
    `;
}

function getExpiryPill(expiresAt) {
    if (!expiresAt) {
        return '<span class="pill active">No expiry</span>';
    }

    const expiryDate = new Date(expiresAt);
    const expired = expiryDate.getTime() < Date.now();
    const css = expired ? "expired" : "active";
    const label = expired ? "Expired" : "Active";
    return `<span class="pill ${css}">${label}</span><div class="muted">${expiresAt}</div>`;
}

async function loadUrls() {
    const tableBody = document.getElementById("url-table-body");
    if (!tableBody) {
        return;
    }

    try {
        const response = await authorizedFetch("/urls");
        const rows = await response.json();
        if (!response.ok) {
            throw new Error(rows.detail || "Failed to load URLs");
        }

        tableBody.innerHTML = "";

        rows.forEach((row) => {
            const tr = document.createElement("tr");
            const shortUrl = `${window.location.origin}/${row.short_code}`;

            tr.innerHTML = `
                <td>${row.id}</td>
                <td><a href="${row.original_url}" target="_blank" rel="noreferrer">${row.original_url}</a></td>
                <td><a href="${shortUrl}" target="_blank" rel="noreferrer">${shortUrl}</a></td>
                <td>${row.clicks}</td>
                <td>${getExpiryPill(row.expires_at)}</td>
                <td>${row.created_at}</td>
                <td><button class="action-delete" data-id="${row.id}">Delete</button></td>
            `;
            tableBody.appendChild(tr);
        });

        tableBody.querySelectorAll(".action-delete").forEach((btn) => {
            btn.addEventListener("click", async () => {
                const id = btn.getAttribute("data-id");
                if (!id) {
                    return;
                }

                const ok = window.confirm("Delete this URL entry?");
                if (!ok) {
                    return;
                }

                const responseDelete = await authorizedFetch(`/urls/${id}`, {
                    method: "DELETE",
                });
                if (responseDelete.ok) {
                    await loadUrls();
                    await loadAnalytics();
                } else {
                    const error = await responseDelete.json();
                    window.alert(error.detail || "Delete failed");
                }
            });
        });
    } catch (error) {
        tableBody.innerHTML = `<tr><td colspan="7">${error.message}</td></tr>`;
    }
}

async function loadAnalytics() {
    const analytics = document.getElementById("analytics");
    if (!analytics) {
        return;
    }

    try {
        const response = await authorizedFetch("/analytics/summary");
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || "Failed to load analytics");
        }
        renderAnalytics(data);
    } catch (error) {
        analytics.innerHTML = `<div class="analytics-card">${error.message}</div>`;
    }
}

function setupLogoutButton() {
    const logoutButton = document.getElementById("logout-btn");
    if (!logoutButton) {
        return;
    }
    if (getToken()) {
        logoutButton.classList.remove("hidden");
    }
    logoutButton.addEventListener("click", () => {
        localStorage.removeItem("access_token");
        window.location.href = "/auth";
    });
}

function enforceAuthForPrivatePages() {
    const hasPrivateContent =
        document.getElementById("shorten-form") || document.getElementById("url-table-body");
    const onAuthPage = Boolean(document.getElementById("login-form"));

    if (hasPrivateContent && !getToken()) {
        clearSessionAndRedirect("Please login to continue");
        return;
    }

    if (onAuthPage && getToken()) {
        setResult("auth-result", "Already logged in. You can open dashboard now.");
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const authMessage = new URLSearchParams(window.location.search).get("msg");
    if (authMessage) {
        setResult("auth-result", authMessage, true);
    }

    setupLogoutButton();
    enforceAuthForPrivatePages();

    const registerForm = document.getElementById("register-form");
    const loginForm = document.getElementById("login-form");
    const shortenForm = document.getElementById("shorten-form");

    if (registerForm) {
        registerForm.addEventListener("submit", registerUser);
    }
    if (loginForm) {
        loginForm.addEventListener("submit", loginUser);
    }
    if (shortenForm) {
        shortenForm.addEventListener("submit", shortenUrl);
    }

    loadUrls();
    loadAnalytics();
});
