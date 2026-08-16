document.addEventListener("DOMContentLoaded", () => {
    const launcher = document.querySelector(
        "[data-support-widget-launcher]"
    );
    const widget = document.querySelector(
        "[data-support-widget]"
    );
    const minimizeButton = document.querySelector(
        "[data-support-widget-minimize]"
    );
    const closeButton = document.querySelector(
        "[data-support-widget-close]"
    );

    if (
        !launcher ||
        !widget ||
        !minimizeButton ||
        !closeButton
    ) {
        return;
    }

    const openWidget = () => {
        widget.hidden = false;
        launcher.setAttribute("aria-expanded", "true");
        minimizeButton.focus();
    };

    const hideWidget = () => {
        widget.hidden = true;
        launcher.setAttribute("aria-expanded", "false");
        launcher.focus();
    };

    launcher.addEventListener("click", openWidget);
    minimizeButton.addEventListener("click", hideWidget);
    closeButton.addEventListener("click", hideWidget);

    document.addEventListener("keydown", (event) => {
        if (
            event.key === "Escape" &&
            !widget.hidden
        ) {
            hideWidget();
        }
    });
});