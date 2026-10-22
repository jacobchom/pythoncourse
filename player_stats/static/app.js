const form = document.getElementById("search-form");
const input = document.getElementById("q");
const statusBox = document.getElementById("status");
const resultsBox = document.getElementById("results");
const detailBox = document.getElementById("detail");

// Build DOM nodes safely (API text never goes in as raw HTML).
function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v);
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : String(child));
  }
  return node;
}

function avatar(src, name) {
  if (src) {
    const img = el("img", { src, alt: "", loading: "lazy", class: "avatar" });
    img.onerror = () => img.replaceWith(initials(name));
    return img;
  }
  return initials(name);
}

function initials(name) {
  const words = (name || "").replace(/\(.*?\)/g, "").match(/[\p{L}\p{N}]+/gu) || ["?"];
  const letters = words.map(w => w[0]).join("").slice(0, 2).toUpperCase();
  return el("div", { class: "avatar initials" }, letters);
}

async function search(query) {
  detailBox.hidden = true;
  resultsBox.hidden = false;
  resultsBox.replaceChildren();
  statusBox.textContent = `Searching every source for “${query}”…`;
  history.replaceState(null, "", `?q=${encodeURIComponent(query)}`);

  let data;
  try {
    const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
    data = await res.json();
  } catch (err) {
    statusBox.textContent = "Couldn't reach the server.";
    return;
  }

  const failed = data.errors.map(e => `${e.source} (${e.error})`).join(", ");
  if (data.message) statusBox.textContent = data.message;
  else if (!data.results.length) statusBox.textContent = `No players found for “${query}”.` + (failed ? ` Unavailable: ${failed}.` : "");
  else statusBox.textContent = `${data.results.length} result(s).` + (failed ? ` Unavailable: ${failed}.` : "");

  for (const r of data.results) {
    resultsBox.append(el("button", { class: "card", type: "button", onclick: () => showPlayer(r) },
      avatar(r.image, r.name),
      el("div", { class: "card-body" },
        el("span", { class: "badge" + (r.has_stats ? "" : " muted") }, r.category),
        el("strong", {}, r.name),
        r.subtitle ? el("small", {}, r.subtitle) : null,
        el("small", { class: "via" }, `via ${r.source_label}`)
      )
    ));
  }
}

async function showPlayer(r) {
  resultsBox.hidden = true;
  detailBox.hidden = false;
  detailBox.replaceChildren(el("p", {}, `Loading ${r.name}…`));

  const back = el("button", { class: "back", type: "button", onclick: () => {
    detailBox.hidden = true; resultsBox.hidden = false;
  } }, "← Back to results");

  let data;
  try {
    const res = await fetch(`/api/player/${r.source}/${encodeURIComponent(r.id)}`);
    data = await res.json();
    if (!res.ok) throw new Error(data.error || res.statusText);
  } catch (err) {
    detailBox.replaceChildren(back, el("p", { class: "error" }, `Couldn't load stats: ${err.message}`));
    return;
  }

  const parts = [
    back,
    el("div", { class: "player-head" },
      avatar(data.image, data.name),
      el("div", {},
        el("h2", {}, data.name),
        data.subtitle ? el("p", { class: "subtitle" }, data.subtitle) : null,
        el("p", { class: "via" }, `Data from ${data.source_label}`)
      )
    ),
    data.note ? el("p", { class: "note" }, data.note) : null,
    el("div", { class: "sections" }, data.sections.map(s =>
      el("div", { class: "stat-block" },
        el("h3", {}, s.title),
        s.text ? el("p", {}, s.text) : el("table", {},
          el("tbody", {}, s.rows.map(([label, value]) =>
            el("tr", {}, el("th", {}, label), el("td", {}, value))))
        )
      )
    )),
    data.links.length ? el("p", { class: "links" }, "More: ",
      data.links.map(([label, url]) => el("a", { href: url, target: "_blank", rel: "noopener" }, label))) : null
  ];
  detailBox.replaceChildren(...parts.filter(Boolean));
  window.scrollTo(0, 0);
}

form.addEventListener("submit", e => {
  e.preventDefault();
  const q = input.value.trim();
  if (q) search(q);
});

const initial = new URLSearchParams(location.search).get("q");
if (initial) { input.value = initial; search(initial); }
