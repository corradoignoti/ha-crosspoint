// Sidebar panel of the CrossPoint integration: browse the library, send and
// remove books and wallpapers. All data comes from the crosspoint/* WebSocket
// commands; nothing is stored in the browser except the selected tab and
// e-reader.

import { LitElement, html, nothing } from "lit";

import { makeLocalize } from "./localize.js";
import { styles } from "./styles.js";

const STORAGE_KEY = "crosspoint-panel";
const RESUBSCRIBE_DELAY_MS = 1500;

function readPrefs() {
  try {
    return JSON.parse(window.localStorage.getItem(STORAGE_KEY)) || {};
  } catch {
    return {};
  }
}

function writePrefs(prefs) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
  } catch {
    // Storage may be unavailable (private mode): preferences are optional.
  }
}

function baseName(file) {
  return file.split("/").pop();
}

class CrossPointPanel extends LitElement {
  static properties = {
    hass: { attribute: false },
    narrow: { type: Boolean },
    panel: { attribute: false },
    _entries: { state: true },
    _entryId: { state: true },
    _state: { state: true },
    _tab: { state: true },
    _filter: { state: true },
    _busy: { state: true },
    _progress: { state: true },
    _modes: { state: true },
    _dialog: { state: true },
    _error: { state: true },
  };

  static styles = styles;

  constructor() {
    super();
    const prefs = readPrefs();
    this._entries = undefined;
    this._entryId = prefs.entryId;
    this._state = undefined;
    this._tab = prefs.tab === "wallpapers" ? "wallpapers" : "books";
    this._filter = "";
    this._busy = new Set();
    this._progress = {};
    this._modes = {};
    this._dialog = undefined;
    this._unsubscribe = undefined;
    this._connected = false;
  }

  connectedCallback() {
    super.connectedCallback();
    this._connected = true;
    if (this.hass) this._load();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this._connected = false;
    this._unsubscribeState();
  }

  willUpdate(changed) {
    if (changed.has("hass")) {
      this._t = makeLocalize(this.hass);
      if (!changed.get("hass") && this._connected) this._load();
    }
  }

  // ---- data -------------------------------------------------------------

  async _load() {
    try {
      this._entries = await this.hass.callWS({ type: "crosspoint/entries" });
    } catch (err) {
      this._error = err.message;
      return;
    }
    if (!this._entries.some((e) => e.entry_id === this._entryId)) {
      this._entryId = this._entries[0]?.entry_id;
    }
    this._subscribe();
  }

  async _subscribe() {
    this._unsubscribeState();
    this._state = undefined;
    if (!this._entryId) return;
    const entryId = this._entryId;
    try {
      this._unsubscribe = await this.hass.connection.subscribeMessage(
        (event) => this._onEvent(entryId, event),
        { type: "crosspoint/subscribe", entry_id: entryId },
      );
    } catch (err) {
      this._error = err.message;
    }
  }

  _unsubscribeState() {
    if (this._unsubscribe) {
      this._unsubscribe().catch(() => {});
      this._unsubscribe = undefined;
    }
  }

  _onEvent(entryId, event) {
    if (entryId !== this._entryId) return;
    if (event.type === "state") {
      this._state = event;
      this._error = undefined;
    } else if (event.type === "progress") {
      this._progress = {
        ...this._progress,
        [`${event.kind}:${event.file}`]: event.received / Math.max(event.total, 1),
      };
    } else if (event.type === "closed") {
      // The entry was reloaded (e.g. options changed): subscribe again.
      this._unsubscribe = undefined;
      setTimeout(() => this._connected && this._load(), RESUBSCRIBE_DELAY_MS);
    }
  }

  _selectEntry(entryId) {
    this._entryId = entryId;
    this._savePrefs();
    this._subscribe();
  }

  _selectTab(tab) {
    this._tab = tab;
    this._savePrefs();
  }

  _savePrefs() {
    writePrefs({ entryId: this._entryId, tab: this._tab });
  }

  // ---- actions ----------------------------------------------------------

  _call(type, data) {
    return this.hass.callWS({ type, entry_id: this._entryId, ...data });
  }

  async _run(key, action) {
    this._busy = new Set(this._busy).add(key);
    try {
      return await action();
    } finally {
      const busy = new Set(this._busy);
      busy.delete(key);
      this._busy = busy;
      const { [key]: _, ...progress } = this._progress;
      this._progress = progress;
    }
  }

  _toast(message) {
    this.dispatchEvent(
      new CustomEvent("hass-notification", {
        detail: { message },
        bubbles: true,
        composed: true,
      }),
    );
  }

  _confirm({ title, text, confirm, danger = false }) {
    return new Promise((resolve) => {
      this._dialog = { title, text, confirm, danger, resolve };
    });
  }

  _closeDialog(result) {
    this._dialog?.resolve(result);
    this._dialog = undefined;
  }

  async _send(kind, item) {
    const key = `${kind}:${item.file}`;
    const name = item.title || baseName(item.file);
    const mode = this._modeOf(item);
    await this._run(key, async () => {
      const options = {};
      if (kind === "wallpaper" && mode === "transparent") {
        const check = await this._call("crosspoint/wallpaper_check", {
          file: item.file,
        });
        if (!check.has_transparency) {
          const ok = await this._confirm({
            title: this._t("confirm_opaque_title"),
            text: this._t("confirm_opaque_text", { name }),
            confirm: this._t("send_anyway"),
          });
          if (!ok) return;
          options.force = true;
        }
      }
      const type = kind === "book" ? "crosspoint/send_book" : "crosspoint/send_wallpaper";
      const data = kind === "book" ? {} : { mode };
      for (;;) {
        try {
          await this._call(type, { file: item.file, ...data, ...options });
          this._toast(this._t("done_sent", { name }));
          return;
        } catch (err) {
          if (err.translation_key === "file_exists_on_device" && !options.overwrite) {
            const ok = await this._confirm({
              title: this._t("confirm_overwrite_title"),
              text: this._t("confirm_overwrite_text", { name }),
              confirm: this._t("replace"),
              danger: true,
            });
            if (!ok) return;
            options.overwrite = true;
            continue;
          }
          this._toast(err.message);
          return;
        }
      }
    });
  }

  async _remove(kind, item) {
    const key = `${kind}:${item.file}`;
    const name = item.title || baseName(item.file);
    const ok = await this._confirm({
      title: this._t("confirm_remove_title"),
      text: this._t("confirm_remove_text", { name }),
      confirm: this._t("remove"),
      danger: true,
    });
    if (!ok) return;
    const type = kind === "book" ? "crosspoint/remove_book" : "crosspoint/remove_wallpaper";
    await this._run(key, async () => {
      try {
        await this._call(type, { file: item.file });
      } catch (err) {
        if (err.translation_key !== "not_on_device") {
          this._toast(err.message);
          return;
        }
        const forget = await this._confirm({
          title: this._t("confirm_forget_title"),
          text: this._t("confirm_forget_text", { name }),
          confirm: this._t("forget"),
        });
        if (!forget) return;
        try {
          await this._call(type, { file: item.file, forget_missing: true });
        } catch (err2) {
          this._toast(err2.message);
          return;
        }
      }
      this._toast(this._t("done_removed", { name }));
    });
  }

  async _rescan() {
    await this._run("rescan", async () => {
      try {
        await this._call("crosspoint/rescan", {});
      } catch (err) {
        this._toast(err.message);
      }
    });
  }

  _modeOf(item) {
    return this._modes[item.file] || item.mode || "normal";
  }

  _setMode(item, mode) {
    this._modes = { ...this._modes, [item.file]: mode };
  }

  // ---- rendering --------------------------------------------------------

  render() {
    if (!this.hass || !this._t) return nothing;
    const t = this._t;
    return html`
      <div class="toolbar">
        <ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>
        <div class="title">${t("title")}</div>
        ${this._entries?.length > 1
          ? html`<select
              aria-label="E-reader"
              @change=${(ev) => this._selectEntry(ev.target.value)}
            >
              ${this._entries.map(
                (e) =>
                  html`<option value=${e.entry_id} ?selected=${e.entry_id === this._entryId}>
                    ${e.title}
                  </option>`,
              )}
            </select>`
          : nothing}
        ${this._state
          ? html`<button
              class="action toolbar-button"
              ?disabled=${this._busy.has("rescan")}
              @click=${this._rescan}
            >
              ${t("rescan")}
            </button>`
          : nothing}
      </div>
      <main>${this._renderMain()}</main>
      ${this._renderDialog()}
    `;
  }

  _renderMain() {
    const t = this._t;
    if (this._error && !this._state) return html`<div class="empty">${this._error}</div>`;
    if (this._entries && this._entries.length === 0) {
      return html`<div class="empty">${t("no_entries")}</div>`;
    }
    const state = this._state;
    if (!state) return html`<div class="empty">${t("loading")}</div>`;

    const items = this._tab === "books" ? state.books : state.wallpapers;
    const filter = this._filter.trim().toLowerCase();
    const visible = filter
      ? items.filter((i) =>
          [i.file, i.title, ...(i.authors || [])]
            .filter(Boolean)
            .some((v) => v.toLowerCase().includes(filter)),
        )
      : items;

    return html`
      <div class="status">
        <span class="chip ${state.online ? "online" : ""}">
          <span class="dot"></span>${state.online ? t("online") : t("offline")}
        </span>
        <span class="device">
          ${t("device_info", { model: state.model.name, host: state.host })}
          ${state.firmware ? html` · ${t("firmware", { version: state.firmware })}` : nothing}
        </span>
      </div>
      ${state.online ? nothing : html`<div class="banner">${t("offline_hint")}</div>`}
      <div class="controls">
        <div class="tabs" role="tablist">
          ${["books", "wallpapers"].map(
            (tab) => html`<button
              class="tab"
              role="tab"
              aria-selected=${this._tab === tab}
              @click=${() => this._selectTab(tab)}
            >
              ${t(`tab_${tab}`)}<span class="count">(${state[tab].length})</span>
            </button>`,
          )}
        </div>
        <input
          type="search"
          placeholder=${t("search")}
          aria-label=${t("search")}
          .value=${this._filter}
          @input=${(ev) => {
            this._filter = ev.target.value;
          }}
        />
      </div>
      ${visible.length === 0
        ? html`<div class="empty">
            ${items.length === 0 ? t(`empty_${this._tab}`) : nothing}
          </div>`
        : html`<div class="grid ${this._tab}">
            ${visible.map((item) =>
              this._tab === "books"
                ? this._renderItem("book", item, state.online)
                : this._renderItem("wallpaper", item, state.online),
            )}
          </div>`}
    `;
  }

  _renderItem(kind, item, online) {
    const t = this._t;
    const key = `${kind}:${item.file}`;
    const busy = this._busy.has(key);
    const progress = this._progress[key];
    const inLibrary = item.status !== "missing_from_library";
    const tracked = item.status !== "not_installed";
    const title = kind === "book" ? item.title || baseName(item.file) : baseName(item.file);
    const mode = this._modeOf(item);

    return html`
      <div class="card">
        <div class="thumb">
          ${item.thumbnail_url
            ? html`<img src=${item.thumbnail_url} alt="" loading="lazy" />`
            : html`<div class="placeholder">${title}</div>`}
        </div>
        <div class="body">
          <div class="name">${title}</div>
          ${kind === "book"
            ? html`<div class="meta">
                ${item.authors?.length ? item.authors.join(", ") : t("unknown_author")}
              </div>`
            : item.mode && tracked
              ? html`<div class="meta">
                  ${t("sent_as", { mode: t(`mode_${item.mode}`).toLowerCase() })}
                </div>`
              : nothing}
          <span class="badge ${item.status}">${t(`status_${item.status}`)}</span>
          ${busy && progress !== undefined
            ? html`<div class="meta">
                  ${t("sending", { percent: Math.round(progress * 100) })}
                </div>
                <div class="progress"><div style="width:${progress * 100}%"></div></div>`
            : nothing}
          ${kind === "wallpaper" && inLibrary
            ? html`<div class="segmented" role="group" aria-label=${t("mode")}>
                ${["normal", "transparent"].map(
                  (m) => html`<button
                    aria-pressed=${mode === m}
                    ?disabled=${busy}
                    @click=${() => this._setMode(item, m)}
                  >
                    ${t(`mode_${m}`)}
                  </button>`,
                )}
              </div>`
            : nothing}
          <div class="actions">
            ${inLibrary
              ? html`<button
                  class="action ${item.status === "installed" ? "secondary" : ""}"
                  ?disabled=${!online || busy}
                  @click=${() => this._send(kind, item)}
                >
                  ${tracked ? t("resend") : t("send")}
                </button>`
              : nothing}
            ${tracked
              ? html`<button
                  class="action danger"
                  ?disabled=${!online || busy}
                  @click=${() => this._remove(kind, item)}
                >
                  ${t("remove")}
                </button>`
              : nothing}
          </div>
        </div>
      </div>
    `;
  }

  _renderDialog() {
    const dialog = this._dialog;
    if (!dialog) return nothing;
    return html`
      <div class="scrim" @click=${(ev) => ev.target === ev.currentTarget && this._closeDialog(false)}>
        <div class="dialog" role="alertdialog" aria-modal="true" aria-label=${dialog.title}>
          <h2>${dialog.title}</h2>
          <p>${dialog.text}</p>
          <div class="actions">
            <button class="action secondary" @click=${() => this._closeDialog(false)}>
              ${this._t("cancel")}
            </button>
            <button
              class="action ${dialog.danger ? "danger" : ""}"
              @click=${() => this._closeDialog(true)}
            >
              ${dialog.confirm}
            </button>
          </div>
        </div>
      </div>
    `;
  }
}

if (!customElements.get("crosspoint-panel")) {
  customElements.define("crosspoint-panel", CrossPointPanel);
}
