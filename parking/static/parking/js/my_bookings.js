document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("form").forEach(form => {
        const button = form.querySelector('button[type="submit"], button');

        if (!button || !button.textContent.toLowerCase().includes("cancel")) {
            return;
        }

        form.addEventListener("submit", event => {
            const confirmed = confirm(
                "Are you sure you want to cancel this booking?"
            );

            if (!confirmed) {
                event.preventDefault();
            }
        });
    });
});