function element(tag, className, text) {
    const item = document.createElement(tag);
    item.className = className;
    if (text !== undefined) item.textContent = text;
    return item;
}

function leadButton(card) {
    const button = element("button", "queue-card");
    button.type = "button";
    button.dataset.caseId = card.id;
    button.dataset.snapshot = card.snapshot;
    button.title = card.id;
    const top = element("span", "card-line");
    const pill = element("span", "card-pattern", card.pattern);
    pill.dataset.pattern = card.pattern;
    top.append(pill, element("span", "card-id", card.id.slice(0, 10)));
    const bottom = element("span", "card-line card-meta");
    const date = element("time", "card-date", card.dateLabel);
    date.dateTime = card.date;
    bottom.append(element("span", "", card.summary), date);
    button.append(top, element("span", "card-title", card.title), bottom);
    return button;
}

export default function ({ parentElement, data, setTriggerValue }) {
    const root = parentElement.querySelector(".queue");
    const scroll = root.querySelector(".queue-scroll");
    const format = new Intl.NumberFormat("en");
    root.querySelector(".queue-count").textContent = format.format(data.count);
    root.querySelector(".queue-page").textContent =
        `Page ${format.format(data.page)} of ${format.format(data.pages)}`;
    root.querySelector('[data-step="-1"]').disabled = data.page === 1;
    root.querySelector('[data-step="1"]').disabled = data.page === data.pages;

    // Keep the scroll position and keyboard focus while choosing a lead on this page.
    if (scroll.dataset.view !== data.view) {
        scroll.replaceChildren(...data.cards.map(leadButton));
        scroll.dataset.view = data.view;
        scroll.scrollTop = 0;
    }
    for (const button of scroll.querySelectorAll(".queue-card")) {
        button.setAttribute("aria-pressed", String(button.dataset.caseId === data.selected[0] &&
            button.dataset.snapshot === data.selected[1]));
    }
    root.onclick = (event) => {
        const card = event.target.closest(".queue-card");
        const pager = event.target.closest("[data-step]");
        if (card && card.getAttribute("aria-pressed") !== "true") {
            setTriggerValue("action", { view: data.view, caseId: card.dataset.caseId,
                snapshot: card.dataset.snapshot });
        } else if (pager && !pager.disabled) {
            setTriggerValue("action", { view: data.view, step: Number(pager.dataset.step) });
        }
    };
}
