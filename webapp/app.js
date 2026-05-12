(function () {
    const tg = window.Telegram && window.Telegram.WebApp;
    if (tg) {
        try { tg.ready(); tg.expand(); } catch (_) {}
    }

    // API хост: тот же origin, что отдаёт статику. Можно переопределить через ?api=
    const params = new URLSearchParams(location.search);
    const API_BASE = params.get("api") || "";

    const state = {
        items: [],
        category: "all",
        query: "",
    };

    const $grid = document.getElementById("grid");
    const $cats = document.getElementById("categories");
    const $loader = document.getElementById("loader");
    const $empty = document.getElementById("empty");
    const $stale = document.getElementById("stale-banner");
    const $search = document.getElementById("search");

    async function loadMenu() {
        try {
            const res = await fetch(`${API_BASE}/api/menu`, { cache: "no-store" });
            if (!res.ok) throw new Error("HTTP " + res.status);
            const data = await res.json();
            state.items = data.items || [];
            $stale.classList.toggle("hidden", !data.stale);
            $loader.classList.add("hidden");
            renderCategories();
            renderGrid();
        } catch (e) {
            $loader.textContent = "Не удалось загрузить меню. Попробуйте позже.";
            console.error(e);
        }
    }

    function categoriesList() {
        const set = new Set(state.items.map((i) => i.category));
        return ["all", ...Array.from(set)];
    }

    function renderCategories() {
        $cats.innerHTML = "";
        const cats = categoriesList();
        for (const c of cats) {
            const btn = document.createElement("button");
            btn.className = "cat-btn" + (state.category === c ? " active" : "");
            btn.textContent = c === "all" ? "Всё" : c;
            btn.onclick = () => {
                state.category = c;
                renderCategories();
                renderGrid();
            };
            $cats.appendChild(btn);
        }
    }

    function renderGrid() {
        const q = state.query.trim().toLowerCase();
        const filtered = state.items.filter((it) => {
            if (state.category !== "all" && it.category !== state.category) return false;
            if (q && !it.name.toLowerCase().includes(q)) return false;
            return true;
        });

        $grid.innerHTML = "";
        $empty.classList.toggle("hidden", filtered.length > 0);

        for (const it of filtered) {
            const card = document.createElement("div");
            card.className = "card" + (it.in_stock ? "" : " out-of-stock");
            const img = it.image_url
                ? `<img src="${it.image_url}" alt="" loading="lazy" onerror="this.style.visibility='hidden'">`
                : `<img alt="" style="visibility:hidden">`;
            const status = it.in_stock ? "" : `<div class="card-status">Нет в наличии</div>`;
            card.innerHTML = `
                ${img}
                <div class="card-body">
                    <p class="card-name">${escapeHtml(it.name)}</p>
                    ${status}
                    <div class="card-price">${formatPrice(it.price)}</div>
                </div>
            `;
            card.onclick = () => openModal(it);
            $grid.appendChild(card);
        }
    }

    function openModal(it) {
        document.getElementById("m-img").src = it.image_url || "";
        document.getElementById("m-img").style.display = it.image_url ? "block" : "none";
        document.getElementById("m-name").textContent = it.name;
        document.getElementById("m-desc").textContent = it.description || "Описание отсутствует.";
        document.getElementById("m-price").textContent = formatPrice(it.price);
        document.getElementById("modal").classList.remove("hidden");
    }

    window.closeModal = function (e) {
        if (e && e.target.id !== "modal") return;
        document.getElementById("modal").classList.add("hidden");
    };

    function formatPrice(p) {
        if (!p) return "—";
        return new Intl.NumberFormat("ru-RU").format(p) + " ₽";
    }

    function escapeHtml(s) {
        return String(s).replace(/[&<>"']/g, (c) => ({
            "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
        }[c]));
    }

    $search.addEventListener("input", (e) => {
        state.query = e.target.value;
        renderGrid();
    });

    loadMenu();
})();
