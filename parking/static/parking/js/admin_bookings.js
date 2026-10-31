document.addEventListener("DOMContentLoaded", () => {
    // Confirm before an administrator cancels a booking.
    document.querySelectorAll("form").forEach(form => {
        const button = form.querySelector("button");

        if (
            button &&
            button.textContent.trim().toLowerCase().includes("cancel")
        ) {
            form.addEventListener("submit", event => {
                if (!confirm("Are you sure you want to cancel this booking?")) {
                    event.preventDefault();
                }
            });
        }
    });

    // Focus the booking search box when the page opens.
    const searchInput = document.querySelector("#search");

    if (searchInput && !searchInput.value) {
        searchInput.focus();
    }
});