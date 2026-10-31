document.addEventListener("DOMContentLoaded", () => {
    const links = document.querySelectorAll("a");

    links.forEach(link => {
        const label = link.textContent.trim().toLowerCase();

        if (label === "logout") {
            link.addEventListener("click", event => {
                if (!confirm("Are you sure you want to log out?")) {
                    event.preventDefault();
                }
            });
        }
    });

    console.log("PARKEASE admin dashboard is ready.");
});