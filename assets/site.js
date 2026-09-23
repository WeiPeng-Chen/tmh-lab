/* TMH Laboratory - sidebar behaviour. */
(function () {
  // ---- Collapsible groups ------------------------------------------------
  function store(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) {} return null; }
  document.querySelectorAll(".nav-toggle").forEach(function (btn) {
    var panel = document.getElementById(btn.getAttribute("aria-controls"));
    var key = "thm-nav-" + btn.getAttribute("aria-controls");
    var saved = store(key);
    if (saved !== null && !btn.classList.contains("has-current")) set(saved === "1");
    btn.addEventListener("click", function () {
      var open = btn.getAttribute("aria-expanded") !== "true";
      set(open); store(key, open ? "1" : "0");
    });
    function set(open) { btn.setAttribute("aria-expanded", open); panel.hidden = !open; }
  });

  // ---- Mobile drawer -------------------------------------------------------
  var menu = document.querySelector(".menu-btn");
  if (menu) menu.addEventListener("click", function () {
    var open = document.body.classList.toggle("nav-open");
    menu.setAttribute("aria-expanded", open);
  });
})();

/* ---- Members gate: decrypts the page body in the browser (AES-GCM, PBKDF2-SHA256). ---- */
(function () {
  var gate = document.getElementById("gate");
  if (!gate) return;
  var form = document.getElementById("gate-form"), input = document.getElementById("gate-pw"), msg = document.getElementById("gate-msg");
  var KEY = "thm-members-pw";
  function get() { try { return sessionStorage.getItem(KEY); } catch (e) { return null; } }
  function put(v) { try { v ? sessionStorage.setItem(KEY, v) : sessionStorage.removeItem(KEY); } catch (e) {} }
  function bytes(b64) { var s = atob(b64), a = new Uint8Array(s.length); for (var i = 0; i < s.length; i++) a[i] = s.charCodeAt(i); return a; }

  async function decrypt(pw) {
    var raw = bytes(gate.getAttribute("data-payload"));
    var salt = raw.slice(0, 16), iv = raw.slice(16, 28), ct = raw.slice(28);
    var base = await crypto.subtle.importKey("raw", new TextEncoder().encode(pw), "PBKDF2", false, ["deriveKey"]);
    var key = await crypto.subtle.deriveKey({ name: "PBKDF2", salt: salt, iterations: 200000, hash: "SHA-256" }, base, { name: "AES-GCM", length: 256 }, false, ["decrypt"]);
    return new TextDecoder().decode(await crypto.subtle.decrypt({ name: "AES-GCM", iv: iv }, key, ct));
  }
  function show(html) {
    var box = document.createElement("div");
    box.innerHTML = '<p class="small"><button type="button" class="linklike" id="relock">重新上鎖</button></p>' + html;
    gate.replaceWith(box);
    document.getElementById("relock").addEventListener("click", function () { put(null); location.reload(); });
  }
  async function attempt(pw, quiet) {
    try { show(await decrypt(pw)); put(pw); return true; }
    catch (e) { if (!quiet) msg.textContent = "密碼不正確，請再試一次。"; put(null); return false; }
  }

  if (!(window.crypto && crypto.subtle)) {
    msg.textContent = "此瀏覽器無法解鎖，請改用 Chrome 或 Edge 開啟。";
    return;
  }
  form.addEventListener("submit", function (e) { e.preventDefault(); msg.textContent = ""; attempt(input.value, false); });
  var saved = get(); if (saved) attempt(saved, true);
})();

/* ---- Publications: highlight papers of a research area (publications.html#area=<id>) ---- */
(function () {
  var banner = document.getElementById("area-banner");
  if (!banner) return;
  var names = JSON.parse(banner.getAttribute("data-names"));
  function apply() {
    var m = /^#area=([a-z0-9-]+)$/.exec(location.hash), items = document.querySelectorAll("li[data-areas]");
    items.forEach(function (li) { li.classList.remove("hl"); });
    if (!m || !names[m[1]]) { banner.hidden = true; return; }
    var hits = [];
    items.forEach(function (li) { if ((" " + li.getAttribute("data-areas") + " ").indexOf(" " + m[1] + " ") > -1) { li.classList.add("hl"); hits.push(li); } });
    document.getElementById("area-name").textContent = names[m[1]];
    document.getElementById("area-n").textContent = hits.length;
    banner.hidden = false;
    if (hits[0]) hits[0].scrollIntoView({ block: "center" });
  }
  document.getElementById("area-clear").addEventListener("click", function (e) { e.preventDefault(); history.replaceState(null, "", location.pathname); apply(); window.scrollTo(0, 0); });
  window.addEventListener("hashchange", apply);
  apply();
})();
