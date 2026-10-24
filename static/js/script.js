/**
 * Village Digital Service & Request Management System
 * Client-Side JavaScript
 */

document.addEventListener("DOMContentLoaded", function () {
    console.log("Village Digital Service System: JavaScript initialized successfully.");

    // Update dynamically generated year if element exists
    const yearSpan = document.getElementById("current-year");
    if (yearSpan) {
        yearSpan.textContent = new Date().getFullYear();
    }
});
