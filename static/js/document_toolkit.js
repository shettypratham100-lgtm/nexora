// document_toolkit.js
//
// Shows the selected file's name (and size) inside the dropzone for
// every simple single-file upload tool (Compress, Split, Rotate,
// Watermark, Page Numbers, PDF<->DOCX, PPT to PDF, etc).
//
// Merge PDF and Image to PDF are multi-file tools with their own
// dedicated preview UI (a file list / image grid) and their file
// inputs don't carry a `name` attribute until submit time, so the
// selector below leaves them alone on purpose.

document.addEventListener("DOMContentLoaded", function () {

    function formatSize(bytes) {
        if (bytes < 1024) return bytes + " B";
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
        return (bytes / (1024 * 1024)).toFixed(1) + " MB";
    }

    document.querySelectorAll(".file-dropzone input[type='file'][name]").forEach(function (input) {

        const dropzone = input.closest(".file-dropzone");
        if (!dropzone) return;

        const iconEl = dropzone.querySelector("i");
        const titleEl = dropzone.querySelector(".dropzone-title");
        const hintEl = dropzone.querySelector(".dropzone-hint");
        if (!titleEl) return;

        const defaults = {
            icon: iconEl ? iconEl.className : "",
            title: titleEl.textContent,
            hint: hintEl ? hintEl.textContent : ""
        };

        input.addEventListener("change", function () {

            if (input.files && input.files.length) {

                const file = input.files[0];

                dropzone.classList.add("has-file");
                if (iconEl) iconEl.className = "bi bi-file-earmark-check-fill";
                titleEl.textContent = file.name;
                if (hintEl) hintEl.textContent = formatSize(file.size) + " \u2014 click to change file";

            } else {

                dropzone.classList.remove("has-file");
                if (iconEl) iconEl.className = defaults.icon;
                titleEl.textContent = defaults.title;
                if (hintEl) hintEl.textContent = defaults.hint;

            }

        });

    });

});
