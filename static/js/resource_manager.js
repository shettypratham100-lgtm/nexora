// ======================================================
// RESOURCE MANAGER JAVASCRIPT
// ======================================================
//
// Handles:
//
// • AI Hover Preview
// • Preview Cache
// • Hover Delay
// • Smart Positioning
// • Expand / Collapse Summary
// • Keyword Highlighting
//
// ======================================================



// ======================================================
// GLOBAL VARIABLES
// ======================================================

// Delay before showing preview
let hoverTimer = null;

// Delay before hiding preview
let hideTimer = null;

// Stores preview JSON received from Django
const previewCache = {};



// ======================================================
// POSITION HOVER CARD
// ======================================================
//
// Keeps the preview inside the browser window.
//

function positionHoverCard(hoverCard, event) {

    const OFFSET = 18;

    // Width depends on expanded state
    const cardWidth = hoverCard.classList.contains("expanded")
        ? 500
        : 360;

    const cardHeight = hoverCard.offsetHeight || 260;

    let left = event.pageX + OFFSET;
    let top = event.pageY + OFFSET;

    // Right edge

    if (left + cardWidth > window.innerWidth) {

        left = event.pageX - cardWidth - OFFSET;

    }

    // Bottom edge

    if (top + cardHeight > window.scrollY + window.innerHeight) {

        top = event.pageY - cardHeight - OFFSET;

    }

    hoverCard.style.left = left + "px";
    hoverCard.style.top = top + "px";

}



// ======================================================
// REMOVE GEMINI MARKDOWN
// ======================================================
//
// Gemini sometimes returns:
//
// `Navigator.push()`
//
// We don't want the backticks.
//

function cleanSummary(summary) {

    if (!summary) {

        return "";

    }

    return summary.replace(/`/g, "");

}



// ======================================================
// SHORT SUMMARY
// ======================================================

function truncateSummary(summary) {

    const MAX = 260;

    summary = cleanSummary(summary);

    if (summary.length <= MAX) {

        return summary;

    }

    return summary.substring(0, MAX) + "...";

}



// ======================================================
// HIGHLIGHT AI KEYWORDS
// ======================================================

function highlightKeywords(summary, keywords) {

    if (!keywords) {

        return summary;

    }

    let result = summary;

    const keywordList = keywords
        .split(",")
        .map(keyword => keyword.trim())
        .filter(keyword => keyword.length);

    keywordList.forEach(keyword => {

        const escaped = keyword.replace(

            /[.*+?^${}()|[\]\\]/g,

            "\\$&"

        );

        const regex = new RegExp(

            `(${escaped})`,

            "gi"

        );

        result = result.replace(

            regex,

            "<strong>$1</strong>"

        );

    });

    return result;

}



// ======================================================
// BUILD PREVIEW CARD
// ======================================================
//
// expanded = false
//      Small Preview
//
// expanded = true
//      Full Summary
//

function renderPreviewCard(data, resourceId, expanded = false) {

    const summary = expanded
        ? cleanSummary(data.summary)
        : truncateSummary(data.summary);

    const button = expanded

        ? `
            <a
                href="#"
                class="show-less"
                data-resource-id="${resourceId}"
            >

                ▲ Show Less

            </a>
        `

        : `
            <a
                href="#"
                class="read-summary"
                data-resource-id="${resourceId}"
            >

                Read Full Summary →

            </a>
        `;

    return `

        <div class="d-flex justify-content-between align-items-center mb-2">

            <strong>

                ${data.title}

            </strong>

            <span class="badge bg-primary">

                ${data.type}

            </span>

        </div>

        <hr>

        <div class="small preview-summary">

            ${highlightKeywords(summary, data.keywords)}

        </div>

        <div class="mt-3">

            ${button}

        </div>

    `;

}

// ======================================================
// MAIN SCRIPT
// ======================================================

document.addEventListener("DOMContentLoaded", () => {

    // ==================================================
    // CREATE ONE REUSABLE HOVER CARD
    // ==================================================

    const hoverCard = document.createElement("div");

    hoverCard.className = "resource-hover-card";

    document.body.appendChild(hoverCard);

    let currentResourceId = null;

    let currentMouseEvent = null;

    // ==================================================
    // KEEP POPUP OPEN
    // ==================================================

    hoverCard.addEventListener("mouseenter", () => {

        clearTimeout(hideTimer);

    });

    hoverCard.addEventListener("mouseleave", () => {

        hideTimer = setTimeout(() => {

            hoverCard.style.display = "none";

            hoverCard.classList.remove("expanded");

        }, 200);

    });

    // ==================================================
    // READ MORE / SHOW LESS
    // ==================================================

    hoverCard.addEventListener("click", function (e) {

        const data = previewCache[currentResourceId];

        // ------------------------------
        // READ FULL SUMMARY
        // ------------------------------

        if (e.target.classList.contains("read-summary")) {

            e.preventDefault();

            hoverCard.classList.add("expanded");

            hoverCard.innerHTML = renderPreviewCard(

                data,

                currentResourceId,

                true

            );

            positionHoverCard(

                hoverCard,

                currentMouseEvent

            );

        }

        // ------------------------------
        // SHOW LESS
        // ------------------------------

        if (e.target.classList.contains("show-less")) {

            e.preventDefault();

            hoverCard.classList.remove("expanded");

            hoverCard.innerHTML = renderPreviewCard(

                data,

                currentResourceId,

                false

            );

            positionHoverCard(

                hoverCard,

                currentMouseEvent

            );

        }

    });

    // ==================================================
    // RESOURCE EVENTS
    // ==================================================

    document.querySelectorAll(".resource-preview").forEach(resource => {

        // =============================================
        // MOUSE ENTER
        // =============================================

        resource.addEventListener("mouseenter", function (e) {

            clearTimeout(hideTimer);

            currentMouseEvent = e;

            currentResourceId = this.dataset.resourceId;

            hoverTimer = setTimeout(async () => {

                // =====================================
                // CACHE HIT
                // =====================================

                if (previewCache[currentResourceId]) {

                    hoverCard.classList.remove("expanded");

                    hoverCard.innerHTML = renderPreviewCard(

                        previewCache[currentResourceId],

                        currentResourceId

                    );

                    hoverCard.style.display = "block";

                    positionHoverCard(

                        hoverCard,

                        currentMouseEvent

                    );

                    return;

                }

                // =====================================
                // LOADING
                // =====================================

                hoverCard.innerHTML = `

                    <div class="text-center py-3">

                        🤖 Preparing AI Preview...

                    </div>

                `;

                hoverCard.style.display = "block";

                positionHoverCard(

                    hoverCard,

                    currentMouseEvent

                );

                // =====================================
                // FETCH
                // =====================================

                try {

                    const response = await fetch(

                        `/resources/preview/${currentResourceId}/`

                    );

                    if (!response.ok) {

                        throw new Error();

                    }

                    const data = await response.json();

                    previewCache[currentResourceId] = data;

                    hoverCard.innerHTML = renderPreviewCard(

                        data,

                        currentResourceId

                    );

                    positionHoverCard(

                        hoverCard,

                        currentMouseEvent

                    );

                }

                catch {

                    hoverCard.innerHTML = `

                        <div class="text-danger">

                            Unable to load preview.

                        </div>

                    `;

                }

            }, 800);

        });

        // =============================================
        // MOUSE LEAVE
        // =============================================

        resource.addEventListener("mouseleave", () => {

            clearTimeout(hoverTimer);

            hideTimer = setTimeout(() => {

                hoverCard.style.display = "none";

                hoverCard.classList.remove("expanded");

            }, 200);

        });

    });

});

// ======================================================
// LIVE SEARCH PANEL
//
// Two states:
// 1. Input focused + empty -> show the user's recent
//    searches (rendered server-side, cloned from the
//    <template id="recentSearchesTemplate"> in navbar.html).
// 2. Input has 2+ characters -> live AJAX suggestions from
//    /resources/search-suggestions/, debounced.
// ======================================================

document.addEventListener("DOMContentLoaded", () => {

    const searchInput = document.getElementById("globalSearch");
    const panel = document.getElementById("liveSearchPanel");
    const recentTemplate = document.getElementById("recentSearchesTemplate");

    if (!searchInput || !panel) {
        return;
    }

    let debounceTimer = null;

    // ==========================================
    // SHOW PANEL WHEN SEARCH BAR IS CLICKED
    // ==========================================

    searchInput.addEventListener("focus", function () {

        panel.style.display = "block";

        if (searchInput.value.trim().length >= 2) {
            fetchSuggestions(searchInput.value.trim());
        } else {
            showRecentSearches();
        }

    });

    // ==========================================
    // LIVE SUGGESTIONS AS THE USER TYPES
    // ==========================================

    searchInput.addEventListener("input", function () {

        const query = searchInput.value.trim();

        clearTimeout(debounceTimer);

        if (query.length < 2) {
            showRecentSearches();
            return;
        }

        debounceTimer = setTimeout(() => {
            fetchSuggestions(query);
        }, 250);

    });

    // ==========================================
    // HIDE PANEL WHEN CLICKING OUTSIDE
    // ==========================================

    document.addEventListener("click", function (e) {

        if (
            !panel.contains(e.target) &&
            e.target !== searchInput
        ) {

            panel.style.display = "none";

        }

    });

    // ==========================================
    // CLICK A RECENT SEARCH -> RUN IT
    // ==========================================

    panel.addEventListener("click", function (e) {

        const recentItem = e.target.closest(".recent-search-item[data-query]");

        if (recentItem) {
            searchInput.value = recentItem.dataset.query;
            searchInput.closest("form").submit();
        }

    });

    // ==========================================
    // SHOW RECENT SEARCHES (cloned from the
    // server-rendered <template>)
    // ==========================================

    function showRecentSearches() {

        panel.innerHTML = "";

        if (recentTemplate) {
            panel.appendChild(recentTemplate.content.cloneNode(true));
        }

    }

    // ==========================================
    // FETCH + RENDER LIVE SUGGESTIONS
    // ==========================================

    function fetchSuggestions(query) {

        fetch(
            "/resources/search-suggestions/?q=" + encodeURIComponent(query),
            { headers: { "X-Requested-With": "XMLHttpRequest" } }
        )
            .then(response => response.json())
            .then(suggestions => renderSuggestions(suggestions, query))
            .catch(() => {
                panel.innerHTML = `
                    <div class="live-search-header">Search</div>
                    <div class="recent-search-item text-muted" style="cursor:default;">
                        Couldn't load suggestions right now.
                    </div>
                `;
            });

    }

    function renderSuggestions(suggestions, query) {

        if (!suggestions.length) {

            panel.innerHTML = `
                <div class="live-search-header">Search</div>
                <div class="recent-search-item text-muted" style="cursor:default;">
                    No resources matching "${escapeHtml(query)}"
                </div>
            `;

            return;
        }

        const rows = suggestions.map(function (item) {

            const target = item.external ? ' target="_blank" rel="noopener"' : "";

            return `
                <a href="${item.url}"${target} class="recent-search-item text-decoration-none">
                    <i class="bi bi-file-earmark"></i>
                    <span>
                        ${escapeHtml(item.title)}
                        <span class="text-muted" style="font-size:0.78rem;">
                            &middot; ${escapeHtml(item.type)} in ${escapeHtml(item.collection)}
                        </span>
                    </span>
                </a>
            `;

        }).join("");

        panel.innerHTML = `
            <div class="live-search-header">Resources</div>
            ${rows}
        `;

    }

    function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

});

// ======================================================
// SIDEBAR COLLAPSE TOGGLE
// ======================================================
//
// Same body.sidebar-collapsed class drives two different
// behaviors depending on viewport width (see base.css):
// desktop -> icon-only collapsed sidebar (persisted across
// page loads via localStorage). mobile -> off-canvas drawer
// (must NOT persist -- a drawer should always start closed
// on a fresh page load, only opened by an explicit tap).
// ======================================================

document.addEventListener("DOMContentLoaded", () => {

    const toggleBtn = document.getElementById("sidebarToggleBtn");
    const backdrop = document.getElementById("sidebarBackdrop");

    if (!toggleBtn) {
        return;
    }

    function isMobileWidth() {
        return window.innerWidth < 768;
    }

    // Only restore the persisted collapsed state on desktop --
    // on mobile this would wrongly pop the drawer open on
    // every single page load.
    try {
        if (!isMobileWidth() && localStorage.getItem("nexora-sidebar-collapsed") === "true") {
            document.body.classList.add("sidebar-collapsed");
        }
    } catch (e) {}

    toggleBtn.addEventListener("click", function () {

        document.body.classList.toggle("sidebar-collapsed");

        const isOpen = document.body.classList.contains("sidebar-collapsed");

        // Persisting is only meaningful for the desktop
        // icon-only mode, not the mobile drawer.
        if (!isMobileWidth()) {
            try {
                localStorage.setItem("nexora-sidebar-collapsed", isOpen);
            } catch (e) {}
        }

    });

    // Tapping the dimmed backdrop closes the mobile drawer.
    if (backdrop) {
        backdrop.addEventListener("click", function () {
            document.body.classList.remove("sidebar-collapsed");
            if (!isMobileWidth()) {
                try { localStorage.setItem("nexora-sidebar-collapsed", "false"); } catch (e) {}
            }
        });
    }

});




// ======================================================
// SHARED STYLED CONFIRM MODAL
//
// Replaces native browser confirm() dialogs. Any form
// with data-confirm-title / data-confirm-message has its
// submission intercepted -- the styled modal opens
// instead, and only submits the form if the user clicks
// "Confirm".
// ======================================================

document.addEventListener("DOMContentLoaded", () => {

    const modalEl = document.getElementById("confirmActionModal");

    if (!modalEl || typeof bootstrap === "undefined") {
        return;
    }

    const modal = new bootstrap.Modal(modalEl);
    const titleEl = document.getElementById("confirmActionTitle");
    const messageEl = document.getElementById("confirmActionMessage");
    const confirmBtn = document.getElementById("confirmActionButton");
    const confirmBtnLabel = document.getElementById("confirmActionButtonLabel");

    let pendingForm = null;

    document.addEventListener("submit", function (event) {

        const form = event.target;

        if (!(form instanceof HTMLFormElement) || !form.dataset.confirmTitle) {
            return;
        }

        event.preventDefault();

        pendingForm = form;

        titleEl.textContent = form.dataset.confirmTitle || "Confirm Action";
        messageEl.textContent = form.dataset.confirmMessage || "Are you sure?";
        confirmBtnLabel.textContent = form.dataset.confirmButtonLabel || "Confirm";

        modal.show();

    });

    confirmBtn.addEventListener("click", function () {

        modal.hide();

        if (pendingForm) {
            pendingForm.submit();
            pendingForm = null;
        }

    });

});
