document.addEventListener("DOMContentLoaded", () => {
    const logoutLink = [...document.querySelectorAll("a")].find(link =>
        link.textContent.trim().toLowerCase() === "logout"
    );

    if (logoutLink) {
        logoutLink.addEventListener("click", event => {
            if (!confirm("Are you sure you want to log out?")) {
                event.preventDefault();
            }
        });
    }
});