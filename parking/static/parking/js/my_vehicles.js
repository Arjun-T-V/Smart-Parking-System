document.addEventListener("DOMContentLoaded", () => {
    const numberInput = document.querySelector("#vehicle_number");

    if (numberInput) {
        numberInput.addEventListener("input", () => {
            const cursorPosition = numberInput.selectionStart;
            numberInput.value = numberInput.value.toUpperCase();

            if (cursorPosition !== null) {
                numberInput.setSelectionRange(
                    cursorPosition,
                    cursorPosition
                );
            }
        });
    }

    const form = document.querySelector("form");

    if (form) {
        form.addEventListener("submit", event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                form.reportValidity();
            }
        });
    }
});