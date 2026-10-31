document.addEventListener("DOMContentLoaded", () => {
    const startInput = document.querySelector("#start_time");
    const endInput = document.querySelector("#end_time");

    if (!startInput || !endInput) return;

    function validateTimes() {
        if (startInput.value) {
            endInput.min = startInput.value;
        }

        if (
            startInput.value &&
            endInput.value &&
            endInput.value <= startInput.value
        ) {
            endInput.setCustomValidity(
                "Departure time must be later than arrival time."
            );
        } else {
            endInput.setCustomValidity("");
        }
    }

    startInput.addEventListener("change", validateTimes);
    endInput.addEventListener("change", validateTimes);

    const searchForm = startInput.closest("form");

    if (searchForm) {
        searchForm.addEventListener("submit", event => {
            validateTimes();

            if (!searchForm.checkValidity()) {
                event.preventDefault();
                searchForm.reportValidity();
            }
        });
    }
});