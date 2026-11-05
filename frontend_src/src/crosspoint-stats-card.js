// Lovelace card showing CrossPoint Sync reading statistics for one or more
// users, side by side. It reads the sensor entities of the integration, so it
// needs no configuration: by default it shows every reading stats user.
//
//   type: custom:crosspoint-stats-card
//   title: Reading stats      # optional
//   users: [alice, bob]       # optional, default: all users

import { LitElement, css, html, nothing } from "lit";

import { makeLocalize } from "./localize.js";

const DEVICE_PREFIX = "CrossPoint Sync ";
const NUMBER_STATS = [
  "books_finished",
  "pages_read",
  "reading_sessions",
  "current_streak",
  "longest_streak",
];

/** Find the reading stats users and their sensor entity ids. */
function findUsers(hass) {
  const byDevice = new Map();
  for (const entry of Object.values(hass.entities || {})) {
    if (entry.platform !== "crosspoint" || !entry.device_id || !entry.translation_key) {
      continue;
    }
    if (!byDevice.has(entry.device_id)) byDevice.set(entry.device_id, {});
    byDevice.get(entry.device_id)[entry.translation_key] = entry.entity_id;
  }
  const users = [];
  for (const [deviceId, entities] of byDevice) {
    if (!entities.reading_time) continue;
    const device = hass.devices?.[deviceId];
    const deviceName = device?.name_by_user || device?.name || "";
    const name = deviceName.startsWith(DEVICE_PREFIX)
      ? deviceName.slice(DEVICE_PREFIX.length)
      : deviceName;
    users.push({ deviceId, name, entities });
  }
  return users.sort((a, b) => a.name.localeCompare(b.name));
}

class CrossPointStatsCard extends LitElement {
  static properties = {
    hass: { attribute: false },
    _config: { state: true },
  };

  static getStubConfig() {
    return {};
  }

  setConfig(config) {
    if (config.users !== undefined && !Array.isArray(config.users)) {
      throw new Error("users must be a list of user names");
    }
    this._config = config;
  }

  getCardSize() {
    return 5;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6, rows: "auto" };
  }

  _users() {
    const users = findUsers(this.hass);
    const wanted = this._config.users;
    if (!wanted?.length) return users;
    return wanted
      .map((name) => users.find((u) => u.name === name))
      .filter(Boolean);
  }

  _state(entityId) {
    return entityId ? this.hass.states[entityId] : undefined;
  }

  _number(entityId) {
    const value = Number(this._state(entityId)?.state);
    return Number.isFinite(value) ? value : undefined;
  }

  _moreInfo(entityId) {
    this.dispatchEvent(
      new CustomEvent("hass-more-info", {
        detail: { entityId },
        bubbles: true,
        composed: true,
      }),
    );
  }

  _formatDuration(state) {
    const t = this._t;
    if (!state) return "—";
    // The sensor may be displayed in any time unit: normalize to minutes.
    const factor = { s: 1 / 60, min: 1, h: 60, d: 1440 }[
      state.attributes.unit_of_measurement
    ];
    const value = Number(state.state);
    if (!Number.isFinite(value) || factor === undefined) return "—";
    const total = Math.round(value * factor);
    const hours = Math.floor(total / 60);
    const minutes = total % 60;
    return hours
      ? t("hours_minutes", { hours, minutes })
      : t("minutes", { minutes });
  }

  _formatStat(key, entityId) {
    const value = this._number(entityId);
    if (value === undefined) return "—";
    const number = value.toLocaleString(this.hass.locale?.language);
    return key.endsWith("streak") ? this._t("days", { count: number }) : number;
  }

  render() {
    if (!this.hass || !this._config) return nothing;
    this._t = makeLocalize(this.hass);
    const t = this._t;
    const users = this._users();
    const title = this._config.title ?? t("stats_title");
    const compare = users.length > 1;

    // When comparing, highlight the best value of each statistic.
    const best = {};
    if (compare) {
      for (const key of ["reading_time", ...NUMBER_STATS]) {
        best[key] = Math.max(
          ...users.map((u) => this._number(u.entities[key]) ?? -Infinity),
        );
      }
    }

    return html`
      <ha-card .header=${title || undefined}>
        <div class="content ${title ? "" : "no-header"}">
          ${users.length === 0
            ? html`<div class="empty">${t("stats_no_users")}</div>`
            : html`<div class="users ${compare ? "compare" : ""}">
                ${users.map((user) => this._renderUser(user, compare ? best : {}))}
              </div>`}
        </div>
      </ha-card>
    `;
  }

  _renderUser(user, best) {
    const t = this._t;
    const reading = this._state(user.entities.reading_time);
    const unavailable = !reading || reading.state === "unavailable";
    const isBest = (key) =>
      best[key] !== undefined &&
      best[key] > 0 &&
      this._number(user.entities[key]) === best[key];

    return html`
      <div class="user">
        <div class="name">${user.name}</div>
        ${unavailable
          ? html`<div class="empty">${t("stats_unavailable")}</div>`
          : html`
              <button
                class="hero ${isBest("reading_time") ? "best" : ""}"
                @click=${() => this._moreInfo(user.entities.reading_time)}
              >
                <span class="value">${this._formatDuration(reading)}</span>
                <span class="label">${t("stat_reading_time")}</span>
              </button>
              <div class="stats">
                ${NUMBER_STATS.map(
                  (key) => html`<button
                    class="stat ${isBest(key) ? "best" : ""}"
                    @click=${() => this._moreInfo(user.entities[key])}
                  >
                    <span class="value">${this._formatStat(key, user.entities[key])}</span>
                    <span class="label">${t(`stat_${key}`)}</span>
                  </button>`,
                )}
              </div>
              ${this._renderWeekdays(reading)}
            `}
      </div>
    `;
  }

  _renderWeekdays(reading) {
    const t = this._t;
    const minutes = reading.attributes.weekday_minutes;
    if (!minutes) return nothing;
    const keys = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
    const labels = t("weekdays").split(",");
    const max = Math.max(1, ...keys.map((k) => minutes[k] || 0));
    return html`
      <div class="weekdays" role="img" aria-label=${t("by_weekday")}>
        <div class="label">${t("by_weekday")}</div>
        <div class="bars">
          ${keys.map(
            (k, i) => html`<div class="bar" title="${labels[i]}: ${t("minutes", {
              minutes: minutes[k] || 0,
            })}">
              <div class="fill" style="height:${((minutes[k] || 0) / max) * 100}%"></div>
              <span>${labels[i]}</span>
            </div>`,
          )}
        </div>
      </div>
    `;
  }

  static styles = css`
    .content {
      padding: 0 16px 16px;
    }
    .content.no-header {
      padding-top: 16px;
    }
    .users {
      display: grid;
      gap: 16px;
    }
    .users.compare {
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    }
    .user {
      display: flex;
      flex-direction: column;
      gap: 10px;
      min-width: 0;
    }
    .users.compare .user {
      padding: 12px;
      border-radius: 12px;
      background: var(--secondary-background-color);
    }
    .name {
      font-weight: 500;
      font-size: 16px;
    }
    button {
      font: inherit;
      color: inherit;
      text-align: left;
      background: none;
      border: none;
      padding: 0;
      cursor: pointer;
    }
    .hero .value {
      display: block;
      font-size: 28px;
      font-weight: 400;
      line-height: 1.2;
    }
    .label {
      display: block;
      font-size: 12px;
      color: var(--secondary-text-color);
    }
    .stats {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
      gap: 10px 12px;
    }
    .stat .value {
      display: block;
      font-size: 18px;
    }
    .best .value {
      color: var(--primary-color);
      font-weight: 500;
    }
    .weekdays .bars {
      display: grid;
      grid-template-columns: repeat(7, 1fr);
      gap: 4px;
      height: 64px;
      margin-top: 6px;
    }
    .bar {
      display: flex;
      flex-direction: column;
      justify-content: flex-end;
      align-items: center;
      gap: 2px;
      min-width: 0;
    }
    .fill {
      width: 100%;
      min-height: 2px;
      border-radius: 3px 3px 0 0;
      background: var(--primary-color);
      opacity: 0.85;
    }
    .bar span {
      font-size: 10px;
      color: var(--secondary-text-color);
    }
    .empty {
      color: var(--secondary-text-color);
      padding: 8px 0;
    }
  `;
}

if (!customElements.get("crosspoint-stats-card")) {
  customElements.define("crosspoint-stats-card", CrossPointStatsCard);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "crosspoint-stats-card")) {
  window.customCards.push({
    type: "crosspoint-stats-card",
    name: "CrossPoint reading stats",
    description: "Reading statistics from CrossPoint Sync, for one or more users.",
    preview: true,
  });
}
