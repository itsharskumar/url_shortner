async function shortenUrl(event) {
    event.preventDefault();

    const input = document.getElementById("original-url");
    const result = document.getElementById("result");

    if (!input || !result) {
        return;
    }

    const originalUrl = input.value.trim();
    if (!originalUrl) {
        return;
    }

    try {
        const response = await fetch("/shorten", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ original_url: originalUrl }),
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
    } catch (error) {
        result.classList.remove("hidden");
        result.textContent = error.message;
    }
}

async function loadUrls() {
    const tableBody = document.getElementById("url-table-body");
    if (!tableBody) {
        return;
    }

    const response = await fetch("/urls");
    const rows = await response.json();

    tableBody.innerHTML = "";

    rows.forEach((row) => {
        const tr = document.createElement("tr");
        const shortUrl = `${window.location.origin}/${row.short_code}`;

        tr.innerHTML = `
            <td>${row.id}</td>
            <td><a href="${row.original_url}" target="_blank" rel="noreferrer">${row.original_url}</a></td>
            <td><a href="${shortUrl}" target="_blank" rel="noreferrer">${shortUrl}</a></td>
            <td>${row.clicks}</td>
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

            const responseDelete = await fetch(`/urls/${id}`, { method: "DELETE" });
            if (responseDelete.ok) {
                await loadUrls();
            } else {
                const error = await responseDelete.json();
                window.alert(error.detail || "Delete failed");
            }
        });
    });
}

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("shorten-form");

    if (form) {
        form.addEventListener("submit", shortenUrl);
    }

    loadUrls();
});
