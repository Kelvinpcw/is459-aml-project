const NS = "http://www.w3.org/2000/svg";

function svgElement(tag, attrs, text) {
    const el = document.createElementNS(NS, tag);
    Object.entries(attrs).forEach(([key, value]) => el.setAttribute(key, value));
    if (text !== undefined) el.textContent = text;
    return el;
}

function moveToward(from, to, distance) {
    const length = Math.hypot(to.x - from.x, to.y - from.y);
    return {
        x: from.x + (to.x - from.x) * distance / length,
        y: from.y + (to.y - from.y) * distance / length,
    };
}

export default function ({ parentElement, data, setTriggerValue }) {
    const host = parentElement.querySelector(".graph-canvas");
    const nodes = new Map(data.nodes.map(node => [node.id, node]));
    const xMax = Math.max(270, ...data.nodes.map(node => Math.abs(node.x) + 85));
    const yMax = Math.max(248, ...data.nodes.map(node => Math.abs(node.y) + 60));
    const svg = svgElement("svg", { role: "group", "aria-label": "Account connections graph" });
    let zoom = host.zoom || 1;
    function view() {
        const x = xMax / zoom;
        const y = yMax / zoom;
        svg.setAttribute("viewBox", `${-x} ${-y} ${2 * x} ${2 * y}`);
        host.zoom = zoom;
    }
    view();

    const defs = svgElement("defs", {});
    for (const [id, color] of [["normal-arrow", "#728881"], ["active-arrow", "#127458"]]) {
        const marker = svgElement("marker", { id, viewBox: "0 0 10 10", refX: 9, refY: 5,
            markerWidth: 9, markerHeight: 9, orient: "auto", markerUnits: "userSpaceOnUse" });
        marker.append(svgElement("path", { d: "M 0 1 L 10 5 L 0 9 Z", fill: color }));
        defs.append(marker);
    }
    svg.append(defs);

    const selectedNodes = new Set();
    const oldFocus = parentElement.activeElement?.getAttribute("data-focus-id");
    for (const edge of data.edges) {
        const from = nodes.get(edge.from);
        const to = nodes.get(edge.to);
        const active = edge.id === data.selected;
        if (active) {
            selectedNodes.add(from.id);
            selectedNodes.add(to.id);
        }
        const delta = { x: to.x - from.x, y: to.y - from.y };
        const length = Math.hypot(delta.x, delta.y);
        const bend = edge.curved ? 34 : 0;
        const control = { x: (from.x + to.x) / 2 - delta.y * bend / length,
            y: (from.y + to.y) / 2 + delta.x * bend / length };
        const start = moveToward(from, control, from.size + 4);
        const end = moveToward(to, control, to.size + 5);
        const d = `M ${start.x} ${start.y} Q ${control.x} ${control.y} ${end.x} ${end.y}`;
        const group = svgElement("g", { class: `edge${active ? " active" : ""}`, tabindex: 0, role: "button",
            "aria-pressed": active, "aria-label": `Payments from ${from.account} to ${to.account}, ${edge.count} payments`,
            "data-edge-id": edge.id, "data-focus-id": "edge-" + edge.id });
        group.append(svgElement("title", {}, `${from.account} → ${to.account} · ${edge.count} payments`));
        group.append(svgElement("path", { class: "edge-hit", d }));
        group.append(svgElement("path", { class: "edge-line", d,
            "marker-end": `url(#${active ? "active-arrow" : "normal-arrow"})` }));
        if (data.edges.length <= 12) {
            const midpoint = { x: (start.x + end.x + 2 * control.x) / 4,
                y: (start.y + end.y + 2 * control.y) / 4 };
            group.append(svgElement("text", { x: midpoint.x, y: midpoint.y,
                class: "edge-label", "text-anchor": "middle", "dominant-baseline": "central" }, edge.count));
        }
        const choose = () => setTriggerValue("arrow", edge.id);
        group.addEventListener("click", choose);
        group.addEventListener("keydown", e => {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                choose();
            }
        });
        svg.append(group);
    }

    for (const node of data.nodes) {
        const group = svgElement("g", { class: "node", tabindex: 0, role: "button",
            "aria-label": "Inspect account " + node.account + " at Bank " + node.bank,
            "aria-pressed": node.id === data.selectedAccount, "data-focus-id": "node-" + node.id });
        const choose = () => setTriggerValue("account", node.id);
        group.addEventListener("click", choose);
        group.addEventListener("keydown", e => {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                choose();
            }
        });
        group.append(svgElement("title", {}, `${node.account} · Bank ${node.bank} · ${node.entity}`));
        group.append(svgElement("circle", { cx: node.x, cy: node.y, r: node.size,
            fill: node.fill, class: selectedNodes.has(node.id) || node.id === data.selectedAccount ? "active-node" : "" }));
        if (data.showLabels) {
            const sideways = Math.abs(node.x) > Math.abs(node.y);
            const direction = Math.sign(node.x) || 1;
            const x = sideways ? node.x + direction * (node.size + 7) : node.x;
            const y = sideways ? node.y + 5 : node.y + (node.y < 0 ? -node.size - 7 : node.size + 17);
            const anchor = sideways ? (direction > 0 ? "start" : "end") : "middle";
            group.append(svgElement("text", { x, y, "text-anchor": anchor }, "…" + node.account.slice(-6)));
        }
        svg.append(group);
    }
    host.replaceChildren(svg);
    if (oldFocus) host.querySelector(`[data-focus-id="${CSS.escape(oldFocus)}"]`)?.focus();
    parentElement.querySelector(".zoom-in").onclick = () => { zoom = Math.min(2.2, zoom * 1.2); view(); };
    parentElement.querySelector(".zoom-out").onclick = () => { zoom = Math.max(0.6, zoom / 1.2); view(); };
    parentElement.querySelector(".zoom-fit").onclick = () => { zoom = 1; view(); };
}
