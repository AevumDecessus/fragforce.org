document.addEventListener('DOMContentLoaded', function () {
    // Find the color picker and hex text input for the color field
    var picker = document.querySelector('input[name="color_0"]');
    var hex = document.querySelector('input[name="color_1"]');
    if (!picker || !hex) return;

    picker.addEventListener('input', function () {
        hex.value = picker.value;
    });

    hex.addEventListener('input', function () {
        // Only sync to picker if it looks like a valid hex color
        if (/^#[0-9a-fA-F]{6}$/.test(hex.value)) {
            picker.value = hex.value;
        }
    });

    hex.addEventListener('blur', function () {
        // Normalize to lowercase on blur
        if (/^#[0-9a-fA-F]{6}$/.test(hex.value)) {
            hex.value = hex.value.toLowerCase();
            picker.value = hex.value;
        }
    });
});
