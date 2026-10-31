document.addEventListener("DOMContentLoaded", () => {
    const form = document.querySelector("form");

    if (!form) return;

    form.addEventListener("submit", event => {
        const username = form.querySelector('[name="username"]');
        const password = form.querySelector('[name="password"]');

        if (username && !username.value.trim()) {
            event.preventDefault();
            alert("Please enter your username.");
            username.focus();
            return;
        }

        if (password && !password.value) {
            event.preventDefault();
            alert("Please enter your password.");
            password.focus();
        }
    });
});