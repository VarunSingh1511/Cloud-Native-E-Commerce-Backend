// DRIPPY: one-page demo shop on top of the existing REST API.
// Security rule for this file: API data is only ever written with textContent
// (never as HTML), so a product name can never inject markup or scripts.
"use strict";

const SIZE_PATTERN = /^(.+) - (S|M|L)$/; // "Heavyweight Hoodie - M" -> base name + size
const SIZE_ORDER = ["S", "M", "L"];
const LOW_STOCK = 3;
const TOKEN_KEY = "drippy.token";
const HERO_PICKS = ["Heavyweight Hoodie", "Varsity Bomber", "Essential Tee"];

const state = {
  token: sessionStorage.getItem(TOKEN_KEY),
  user: null,
  groups: [],
  categories: [],
  stock: new Map(), // product id -> units in stock
  productImage: new Map(), // product id -> image URL
  cart: { items: [], total: 0 },
  category: "all",
  pendingProductId: null, // "Add to bag" clicked before signing in
};

const $ = (id) => document.getElementById(id);
const money = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });

// ---------------------------------------------------------------- API calls
class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

function errorMessage(data) {
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail) && data.detail.length) return data.detail[0].msg; // validation (422)
  return "Something went wrong. Please try again.";
}

async function api(path, { method = "GET", json, form } = {}) {
  const headers = {};
  let body;
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  } else if (form) {
    body = new URLSearchParams(form); // the login endpoint expects an HTML form
  }
  const response = await fetch(path, { method, headers, body });
  if (response.status === 204) return null;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && state.token) signOut(true); // expired or invalid login
    throw new ApiError(response.status, errorMessage(data));
  }
  return data;
}

// ------------------------------------------------------------------ helpers
function toast(message, isError = false) {
  const el = document.createElement("div");
  el.className = isError ? "toast error" : "toast";
  el.textContent = message;
  $("toasts").append(el);
  setTimeout(() => el.remove(), 3200);
}

// Accept Blob Storage (https) or same-site paths ("/..."), never "//other-host" or "javascript:".
function safeImageUrl(url) {
  if (typeof url !== "string") return null;
  return url.startsWith("https://") || /^\/(?!\/)/.test(url) ? url : null;
}

function splitName(name) {
  const match = SIZE_PATTERN.exec(name);
  return match ? { base: match[1], size: match[2] } : { base: name, size: "One size" };
}

// Turn "X - S", "X - M", "X - L" products into one group with three variants.
function groupProducts(products) {
  const groups = new Map();
  for (const product of products) {
    const { base, size } = splitName(product.name);
    if (!groups.has(base)) {
      groups.set(base, { name: base, description: product.description, price: product.price,
        categoryId: product.category_id, image: null, variants: [] });
    }
    const group = groups.get(base);
    group.image = group.image || safeImageUrl(product.image_url);
    group.variants.push({ size, product });
  }
  for (const group of groups.values()) {
    group.variants.sort((a, b) => SIZE_ORDER.indexOf(a.size) - SIZE_ORDER.indexOf(b.size));
    for (const v of group.variants) state.productImage.set(v.product.id, group.image);
  }
  return [...groups.values()];
}

const stockOf = (productId) => state.stock.get(productId) ?? 0;
const inBag = (productId) => state.cart.items.find((item) => item.product_id === productId)?.quantity ?? 0;

// ---------------------------------------------------------------- catalogue
async function loadCatalogue() {
  try {
    const [products, categories] = await Promise.all([api("/products?limit=100"), api("/categories")]);
    state.categories = categories;
    state.groups = groupProducts(products);
    await refreshStock(products.map((p) => p.id));
    renderChips();
    renderGrid();
    renderHeroArt();
  } catch (error) {
    $("grid-message").textContent = "The shop could not be loaded. Please refresh in a moment.";
  }
}

async function refreshStock(productIds) {
  const levels = await Promise.all(productIds.map((id) => api(`/inventory/${id}`).catch(() => null)));
  levels.forEach((level, i) => state.stock.set(productIds[i], level ? level.quantity : 0));
}

function renderChips() {
  // Categories in the order their first product appears in the shop.
  const order = [...new Set(state.groups.map((g) => g.categoryId))];
  const used = state.categories.filter((c) => order.includes(c.id)).sort((a, b) => order.indexOf(a.id) - order.indexOf(b.id));
  const chips = [{ id: "all", name: "All" }, ...used];
  const nav = $("category-chips");
  nav.replaceChildren(...chips.map((c) => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = c.id === state.category ? "chip active" : "chip";
    chip.textContent = c.name;
    chip.addEventListener("click", () => {
      state.category = c.id;
      renderChips();
      renderGrid();
      $("shop").scrollIntoView({ behavior: "smooth" });
    });
    return chip;
  }));
}

function renderHeroArt() {
  const withImages = state.groups.filter((g) => g.image);
  const picks = HERO_PICKS.map((n) => withImages.find((g) => g.name === n)).filter(Boolean);
  const chosen = (picks.length === 3 ? picks : withImages).slice(0, 3);
  $("hero-art").replaceChildren(...chosen.map((g) => {
    const img = document.createElement("img");
    img.src = g.image;
    img.alt = "";
    return img;
  }));
}

function renderGrid() {
  const visible = state.groups.filter((g) => state.category === "all" || g.categoryId === state.category);
  $("shop-count").textContent = `${visible.length} ${visible.length === 1 ? "piece" : "pieces"}`;
  if (!visible.length) {
    const message = document.createElement("p");
    message.className = "muted loading";
    message.textContent = "Nothing here yet. Check back for the next drop.";
    $("product-grid").replaceChildren(message);
    return;
  }
  $("product-grid").replaceChildren(...visible.map((group, i) => buildCard(group, i)));
}

function buildCard(group, index) {
  const card = $("card-template").content.firstElementChild.cloneNode(true);
  card.style.animationDelay = `${index * 60}ms`;
  const media = card.querySelector(".card-media");
  const img = card.querySelector("img");
  if (group.image) {
    img.src = group.image;
    img.alt = group.name;
  } else {
    img.remove();
    const placeholder = document.createElement("div");
    placeholder.className = "placeholder";
    placeholder.textContent = group.name.charAt(0);
    media.prepend(placeholder);
  }
  card.querySelector(".card-title").textContent = group.name;
  card.querySelector(".price").textContent = money.format(group.price);
  card.querySelector(".card-desc").textContent = group.description;

  const badge = card.querySelector(".badge");
  const addButton = card.querySelector(".add-btn");
  const sizeRow = card.querySelector(".sizes");
  const inStock = group.variants.filter((v) => stockOf(v.product.id) > 0);
  let selected = inStock[0] || null;

  const update = () => {
    for (const button of sizeRow.children) button.classList.toggle("selected", button.dataset.id === String(selected?.product.id));
    if (!inStock.length) {
      badge.hidden = false;
      badge.className = "badge soldout";
      badge.textContent = "Sold out";
      card.classList.add("is-soldout");
      addButton.disabled = true;
      addButton.textContent = "Sold out";
      return;
    }
    const left = stockOf(selected.product.id);
    badge.hidden = left > LOW_STOCK;
    badge.className = "badge";
    badge.textContent = `Only ${left} left`;
    addButton.disabled = false;
    addButton.textContent = `Add to bag · ${selected.size}`;
  };

  for (const variant of group.variants) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "size";
    button.textContent = variant.size === "One size" ? "OS" : variant.size;
    button.dataset.id = String(variant.product.id);
    button.disabled = stockOf(variant.product.id) === 0;
    button.setAttribute("aria-label", `Size ${variant.size}${button.disabled ? ", sold out" : ""}`);
    button.addEventListener("click", () => { selected = variant; update(); });
    sizeRow.append(button);
  }
  addButton.addEventListener("click", () => selected && addToBag(selected.product.id));
  update();
  return card;
}

// --------------------------------------------------------------------- bag
async function refreshCart() {
  if (!state.token) {
    state.cart = { items: [], total: 0 };
  } else {
    state.cart = await api("/cart");
  }
  renderBag();
}

async function addToBag(productId) {
  if (!state.token) {
    state.pendingProductId = productId;
    openAuth("login", "Sign in to add items to your bag.");
    return;
  }
  const left = stockOf(productId);
  if (inBag(productId) >= left) {
    toast(`Only ${left} in stock for that size.`, true);
    return;
  }
  try {
    await api("/cart/items", { method: "POST", json: { product_id: productId, quantity: 1 } });
    await refreshCart();
    const count = $("bag-count");
    count.classList.remove("bump");
    void count.offsetWidth; // restart the animation
    count.classList.add("bump");
    toast("Added to bag");
  } catch (error) {
    toast(error.message, true);
  }
}

function renderBag() {
  const count = state.cart.items.reduce((sum, item) => sum + item.quantity, 0);
  $("bag-count").textContent = String(count);
  $("bag-count").hidden = count === 0;
  $("bag-total").textContent = money.format(state.cart.total);
  $("drawer-foot").hidden = count === 0;
  if (!count) {
    $("drawer-body").replaceChildren(message("Your bag is empty", "Pick a size and add something you like."));
    return;
  }
  $("drawer-body").replaceChildren(...state.cart.items.map((item) => {
    const line = $("line-template").content.firstElementChild.cloneNode(true);
    const { base, size } = splitName(item.product_name);
    const image = state.productImage.get(item.product_id);
    if (image) line.querySelector("img").src = image;
    line.querySelector(".line-name").textContent = base;
    line.querySelector(".line-meta").textContent = `Size ${size} · ${money.format(item.unit_price)}`;
    line.querySelector(".qty").textContent = `× ${item.quantity}`;
    line.querySelector(".line-total").textContent = money.format(item.line_total);
    line.querySelector(".plus").addEventListener("click", () => addToBag(item.product_id));
    line.querySelector(".remove").addEventListener("click", async () => {
      try {
        await api(`/cart/items/${item.id}`, { method: "DELETE" });
        await refreshCart();
      } catch (error) {
        toast(error.message, true);
      }
    });
    return line;
  }));
}

function message(title, text) {
  const box = document.createElement("div");
  box.className = "empty";
  const strong = document.createElement("strong");
  strong.textContent = title;
  const p = document.createElement("p");
  p.className = "muted";
  p.textContent = text;
  box.append(strong, p);
  return box;
}

async function checkout() {
  const button = $("checkout-btn");
  button.disabled = true;
  button.textContent = "Placing order…";
  try {
    const order = await api("/orders", { method: "POST" });
    await refreshStock(order.items.map((i) => i.product_id).filter(Boolean));
    renderGrid();
    await refreshCart();
    showSuccess(order);
  } catch (error) {
    toast(error.message, true); // e.g. 409 "Not enough stock for ..."
  } finally {
    button.disabled = false;
    button.textContent = "Checkout";
  }
}

function showSuccess(order) {
  const box = document.createElement("div");
  box.className = "success";
  const tick = document.createElement("div");
  tick.className = "tick";
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", "M5 12.5l4.5 4.5L19 7.5");
  svg.append(path);
  tick.append(svg);
  const title = document.createElement("strong");
  title.textContent = `Order #${order.id} placed`;
  const text = document.createElement("p");
  text.className = "muted";
  text.textContent = `${money.format(order.total_amount)} · we'll let you know when it ships.`;
  const more = document.createElement("button");
  more.className = "ghost-btn";
  more.type = "button";
  more.textContent = "View my orders";
  more.addEventListener("click", () => { closeDrawer(); openOrders(); });
  box.append(tick, title, text, more);
  $("drawer-body").replaceChildren(box);
  $("drawer-foot").hidden = true;
}

function openDrawer() {
  $("overlay").hidden = false;
  $("drawer").classList.add("open");
  $("drawer").setAttribute("aria-hidden", "false");
}

function closeDrawer() {
  $("overlay").hidden = true;
  $("drawer").classList.remove("open");
  $("drawer").setAttribute("aria-hidden", "true");
}

// -------------------------------------------------------------------- auth
let authMode = "login";

function setAuthMode(mode) {
  authMode = mode;
  $("tab-login").classList.toggle("active", mode === "login");
  $("tab-register").classList.toggle("active", mode === "register");
  $("tab-login").setAttribute("aria-selected", String(mode === "login"));
  $("tab-register").setAttribute("aria-selected", String(mode === "register"));
  $("auth-submit").textContent = mode === "login" ? "Sign in" : "Create account";
  $("auth-password").autocomplete = mode === "login" ? "current-password" : "new-password";
  $("auth-error").textContent = "";
}

function openAuth(mode = "login", hint = "") {
  setAuthMode(mode);
  $("auth-error").textContent = hint;
  $("auth-dialog").showModal();
  $("auth-email").focus();
}

async function submitAuth(event) {
  event.preventDefault();
  const email = $("auth-email").value.trim();
  const password = $("auth-password").value;
  if (!email || password.length < 8) {
    $("auth-error").textContent = "Enter your email and a password of at least 8 characters.";
    return;
  }
  $("auth-submit").disabled = true;
  try {
    if (authMode === "register") {
      await api("/auth/register", { method: "POST", json: { email, password } });
    }
    const login = await api("/auth/login", { method: "POST", form: { username: email, password } });
    state.token = login.access_token;
    sessionStorage.setItem(TOKEN_KEY, state.token);
    await loadUser();
    $("auth-dialog").close();
    $("auth-password").value = "";
    toast(authMode === "register" ? "Welcome to DRIPPY" : "Signed in");
    if (state.pendingProductId) {
      const productId = state.pendingProductId;
      state.pendingProductId = null;
      await addToBag(productId);
    }
  } catch (error) {
    $("auth-error").textContent = error.status === 401 ? "Wrong email or password." : error.message;
  } finally {
    $("auth-submit").disabled = false;
  }
}

async function loadUser() {
  if (!state.token) return;
  try {
    state.user = await api("/users/me");
    await refreshCart();
  } catch {
    state.user = null;
  }
  renderAccount();
}

function renderAccount() {
  $("account-btn").textContent = state.user ? state.user.email : "Sign in";
  $("account-btn").title = state.user ? "My orders" : "";
}

function signOut(expired = false) {
  state.token = null;
  state.user = null;
  sessionStorage.removeItem(TOKEN_KEY);
  state.cart = { items: [], total: 0 };
  renderAccount();
  renderBag();
  if ($("orders-dialog").open) $("orders-dialog").close();
  toast(expired ? "Your session ended. Please sign in again." : "Signed out");
}

// ------------------------------------------------------------------ orders
async function openOrders() {
  const isAdmin = state.user?.role === "ADMIN";
  $("orders-title").textContent = isAdmin ? "All orders" : "My orders";
  $("orders-list").replaceChildren(message("Loading…", ""));
  $("orders-dialog").showModal();
  try {
    const orders = await api("/orders");
    if (!orders.length) {
      $("orders-list").replaceChildren(message("No orders yet", "Your first drop is waiting."));
      return;
    }
    $("orders-list").replaceChildren(...orders.map((order) => {
      const box = $("order-template").content.firstElementChild.cloneNode(true);
      box.querySelector(".order-id").textContent = `Order #${order.id}`;
      const pill = box.querySelector(".pill");
      pill.textContent = order.status.charAt(0) + order.status.slice(1).toLowerCase();
      pill.classList.add(order.status);
      box.querySelector(".order-date").textContent = new Date(order.created_at).toLocaleString("en-IN",
        { dateStyle: "medium", timeStyle: "short" });
      box.querySelector(".order-items").replaceChildren(...order.items.map((item) => {
        const li = document.createElement("li");
        li.textContent = `${item.product_name} × ${item.quantity}`;
        return li;
      }));
      box.querySelector(".order-total").textContent = money.format(order.total_amount);
      return box;
    }));
  } catch (error) {
    $("orders-list").replaceChildren(message("Could not load orders", error.message));
  }
}

// ------------------------------------------------------------- API status
async function checkStatus() {
  const status = $("api-status");
  try {
    const [ready, spec] = await Promise.all([api("/health/ready"), api("/openapi.json")]);
    status.className = ready.database === "ok" ? "status ok" : "status down";
    $("api-status-text").textContent = `API v${spec.info.version} live · database connected`;
  } catch {
    status.className = "status down";
    $("api-status-text").textContent = "API unavailable";
  }
}

// -------------------------------------------------------------------- start
function wireEvents() {
  $("bag-btn").addEventListener("click", openDrawer);
  $("drawer-close").addEventListener("click", closeDrawer);
  $("overlay").addEventListener("click", closeDrawer);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDrawer(); });
  $("checkout-btn").addEventListener("click", checkout);
  $("account-btn").addEventListener("click", () => (state.user ? openOrders() : openAuth("login")));
  $("auth-form").addEventListener("submit", submitAuth);
  $("auth-close").addEventListener("click", () => { state.pendingProductId = null; $("auth-dialog").close(); });
  $("tab-login").addEventListener("click", () => setAuthMode("login"));
  $("tab-register").addEventListener("click", () => setAuthMode("register"));
  $("signout-btn").addEventListener("click", () => signOut());
}

wireEvents();
renderBag();
loadCatalogue();
loadUser();
checkStatus();
