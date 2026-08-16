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

    const prefersReducedMotion = window.matchMedia(
        "(prefers-reduced-motion: reduce)"
    ).matches;

    const animationDuration = prefersReducedMotion
        ? 0
        : 220;

    let hideTimer = null;

    const openWidget = () => {
        if (hideTimer) {
            window.clearTimeout(hideTimer);
            hideTimer = null;
        }

        widget.hidden = false;

        window.requestAnimationFrame(() => {
            widget.classList.add("is-open");

            launcher.setAttribute(
                "aria-expanded",
                "true"
            );
        });
    };

    const hideWidget = () => {
        if (widget.hidden) {
            return;
        }

        widget.classList.remove("is-open");

        launcher.setAttribute(
            "aria-expanded",
            "false"
        );

        hideTimer = window.setTimeout(() => {
            widget.hidden = true;
            hideTimer = null;

            launcher.focus();
        }, animationDuration);
    };

    launcher.addEventListener(
        "click",
        openWidget
    );

    minimizeButton.addEventListener(
        "click",
        hideWidget
    );

    closeButton.addEventListener(
        "click",
        hideWidget
    );

    document.addEventListener(
        "keydown",
        (event) => {
            if (
                event.key === "Escape" &&
                !widget.hidden
            ) {
                hideWidget();
            }
        }
    );
});