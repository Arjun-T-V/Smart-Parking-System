document.addEventListener("DOMContentLoaded", () => {
    const paymentForm = document.querySelector("form");

    if (!paymentForm) return;

    paymentForm.addEventListener("submit", event => {
        const clickedButton = event.submitter;

        if (!clickedButton) return;

        if (clickedButton.value === "success") {
            if (!confirm("Simulate a successful demo payment?")) {
                event.preventDefault();
            }
        }

        if (clickedButton.value === "failure") {
            if (!confirm("Simulate a failed demo payment?")) {
                event.preventDefault();
            }
        }
    });
});