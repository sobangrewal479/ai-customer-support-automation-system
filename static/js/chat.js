document.addEventListener("DOMContentLoaded", () => {
    const form = document.querySelector(".chat-form");
    const transcript = document.querySelector(
        ".chat-transcript"
    );
    const widgetMode = document.body.classList.contains(
        "widget-mode"
    );

    if (!form || !transcript) {
        return;
    }

    let isSubmitting = false;

    const scrollToLatestMessage = () => {
        window.requestAnimationFrame(() => {
            transcript.scrollTo({
                top: transcript.scrollHeight,
                behavior: "smooth",
            });
        });
    };

    const getTextarea = () => {
        return form.querySelector("#message");
    };

    const getSubmitButton = () => {
        return form.querySelector(
            'button[type="submit"]'
        );
    };

    const setSubmittingState = (submitting) => {
        isSubmitting = submitting;

        const textarea = getTextarea();
        const submitButton = getSubmitButton();

        form.setAttribute(
            "aria-busy",
            submitting ? "true" : "false"
        );

        transcript.setAttribute(
            "aria-busy",
            submitting ? "true" : "false"
        );

        if (textarea) {
            textarea.disabled = submitting;
        }

        if (submitButton) {
            submitButton.disabled = submitting;

            submitButton.textContent = submitting
                ? "Sending..."
                : "Send message";
        }
    };

    const addTypingIndicator = () => {
        const existingIndicator = transcript.querySelector(
            "[data-typing-indicator]"
        );

        if (existingIndicator) {
            return;
        }

        const indicator = document.createElement(
            "article"
        );

        indicator.className =
            "chat-message chat-message--assistant chat-message--typing";

        indicator.setAttribute(
            "data-typing-indicator",
            ""
        );

        indicator.innerHTML = `
            <p class="chat-message-sender">
                Harbor &amp; Pine Support
            </p>

            <div
                class="typing-indicator"
                aria-label="Harbor & Pine Support is replying"
            >
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;

        transcript.appendChild(indicator);

        scrollToLatestMessage();
    };

    const removeTypingIndicator = () => {
        const indicator = transcript.querySelector(
            "[data-typing-indicator]"
        );

        if (indicator) {
            indicator.remove();
        }
    };

    const showSubmissionError = () => {
        let error = form.querySelector(
            "[data-async-error]"
        );

        if (!error) {
            error = document.createElement("div");

            error.className = "chat-error";
            error.setAttribute(
                "data-async-error",
                ""
            );
            error.setAttribute(
                "role",
                "alert"
            );

            form.prepend(error);
        }

        error.textContent = (
            "The message could not be sent. "
            + "Please try again."
        );
    };

    const updateFromResponse = (html) => {
        const parser = new DOMParser();

        const responseDocument = parser.parseFromString(
            html,
            "text/html"
        );

        const newTranscript =
            responseDocument.querySelector(
                ".chat-transcript"
            );

        const newForm =
            responseDocument.querySelector(
                ".chat-form"
            );

        if (!newTranscript || !newForm) {
            throw new Error(
                "Expected chat content was not returned."
            );
        }

        transcript.innerHTML =
            newTranscript.innerHTML;

        form.innerHTML =
            newForm.innerHTML;

        scrollToLatestMessage();

        const textarea = getTextarea();

        if (textarea) {
            textarea.focus();
        }
    };

    const submitWidgetMessage = async () => {
        if (isSubmitting) {
            return;
        }

        const textarea = getTextarea();

        if (!textarea) {
            return;
        }

        const formData = new FormData(form);

        setSubmittingState(true);
        addTypingIndicator();

        try {
            const response = await fetch(
                window.location.href,
                {
                    method: "POST",
                    body: formData,
                    credentials: "same-origin",
                    headers: {
                        "X-Requested-With":
                            "XMLHttpRequest",
                    },
                }
            );

            if (!response.ok) {
                throw new Error(
                    `Chat request failed: ${response.status}`
                );
            }

            const html = await response.text();

            removeTypingIndicator();

            updateFromResponse(html);
        } catch (error) {
            console.error(error);

            removeTypingIndicator();
            showSubmissionError();
        } finally {
            setSubmittingState(false);
        }
    };

    form.addEventListener(
        "keydown",
        (event) => {
            if (
                event.target.id !== "message"
            ) {
                return;
            }

            const shouldSubmit = (
                event.key === "Enter"
                && !event.shiftKey
                && !event.isComposing
            );

            if (!shouldSubmit) {
                return;
            }

            event.preventDefault();

            form.requestSubmit();
        }
    );

    form.addEventListener(
        "submit",
        (event) => {
            if (!widgetMode) {
                return;
            }

            event.preventDefault();

            submitWidgetMessage();
        }
    );

    scrollToLatestMessage();
});