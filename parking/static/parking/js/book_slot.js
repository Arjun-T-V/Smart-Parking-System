document.addEventListener("DOMContentLoaded", () => {
    const form = document.querySelector("form");
    const start = document.querySelector("#start_time");
    const end = document.querySelector("#end_time");

    if (!form) return;

    function checkTimes() {
        if (start && end) {
            end.min = start.value;

            if (start.value && end.value && end.value <= start.value) {
                end.setCustomValidity(
                    "End time must be later than start time."
                );
            } else {
                end.setCustomValidity("");
            }
        }
    }

    if (start && end) {
        start.addEventListener("change", checkTimes);
        end.addEventListener("change", checkTimes);
    }

    form.addEventListener("submit", event => {
        checkTimes();

        if (!form.checkValidity()) {
            event.preventDefault();
            form.reportValidity();
        }
    });
});