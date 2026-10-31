document.addEventListener("DOMContentLoaded", () => {
    // Highlight the current navigation link.
    const currentPage = window.location.pathname;

    document.querySelectorAll("nav a").forEach(link => {
        if (link.pathname === currentPage) {
            link.style.color = "#2ecc71";
        }
    });

    // Smooth scrolling for links that point to page sections.
    document.querySelectorAll('a[href^="#"]').forEach(link => {
        link.addEventListener("click", event => {
            const target = document.querySelector(link.getAttribute("href"));

            if (target) {
                event.preventDefault();
                target.scrollIntoView({ behavior: "smooth" });
            }
        });
    });
});