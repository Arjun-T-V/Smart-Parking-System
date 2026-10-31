document.addEventListener("DOMContentLoaded", () => {
    const form = document.querySelector("form");

    if (!form) return;

    form.addEventListener("submit", event => {
        const passwordFields = form.querySelectorAll(
            'input[type="password"]'
        );

        // Check password length if the form has a password field.
        for (const field of passwordFields) {
            if (field.value && field.value.length < 8) {
                event.preventDefault();
                alert("Passwords should contain at least 8 characters.");
                field.focus();
                return;
            }
        }

        if (!form.checkValidity()) {
            event.preventDefault();
            form.reportValidity();
        }
    });
});