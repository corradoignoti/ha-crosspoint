import { css } from "lit";

export const styles = css`
  :host {
    display: block;
    min-height: 100vh;
    background: var(--primary-background-color);
    color: var(--primary-text-color);
    font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
    --cp-radius: var(--ha-card-border-radius, 12px);
    --cp-ok: var(--success-color, #43a047);
    --cp-warn: var(--warning-color, #ffa600);
    --cp-error: var(--error-color, #db4437);
    --cp-muted: var(--secondary-text-color);
  }
  .toolbar {
    display: flex;
    align-items: center;
    gap: 8px;
    height: var(--header-height, 56px);
    padding: 0 12px;
    background: var(--app-header-background-color, var(--primary-color));
    color: var(--app-header-text-color, var(--text-primary-color, #fff));
    border-bottom: var(--app-header-border-bottom, none);
    box-sizing: border-box;
  }
  .toolbar .title {
    flex: 1;
    font-size: 20px;
    font-weight: 400;
    margin-left: 8px;
  }
  .toolbar select {
    font: inherit;
    color: inherit;
    background: transparent;
    border: 1px solid currentColor;
    border-radius: 6px;
    padding: 4px 6px;
  }
  .toolbar select option {
    color: var(--primary-text-color);
    background: var(--card-background-color);
  }
  main {
    max-width: 1200px;
    margin: 0 auto;
    padding: 16px;
  }
  .status {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
  }
  .chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: 16px;
    font-size: 13px;
    font-weight: 500;
    background: var(--secondary-background-color);
  }
  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--cp-muted);
  }
  .chip.online .dot {
    background: var(--cp-ok);
  }
  .device {
    color: var(--cp-muted);
    font-size: 14px;
  }
  .spacer {
    flex: 1;
  }
  .banner {
    padding: 12px 16px;
    border-radius: var(--cp-radius);
    background: var(--secondary-background-color);
    border-left: 4px solid var(--cp-warn);
    margin-bottom: 16px;
    font-size: 14px;
  }
  .controls {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    align-items: center;
    margin-bottom: 16px;
  }
  .tabs {
    display: flex;
    border-bottom: 1px solid var(--divider-color);
    flex: 1;
    min-width: 220px;
  }
  .tab {
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    color: var(--cp-muted);
    font: inherit;
    font-weight: 500;
    padding: 10px 16px;
    cursor: pointer;
  }
  .tab[aria-selected="true"] {
    color: var(--primary-color);
    border-bottom-color: var(--primary-color);
  }
  .count {
    font-weight: 400;
    margin-left: 4px;
  }
  input[type="search"] {
    font: inherit;
    padding: 8px 12px;
    border-radius: 8px;
    border: 1px solid var(--divider-color);
    background: var(--card-background-color);
    color: var(--primary-text-color);
    min-width: 200px;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
    gap: 16px;
  }
  .card {
    display: flex;
    flex-direction: column;
    background: var(--card-background-color);
    border-radius: var(--cp-radius);
    box-shadow: var(--ha-card-box-shadow, 0 2px 2px rgba(0, 0, 0, 0.14));
    border: var(--ha-card-border-width, 1px) solid
      var(--ha-card-border-color, var(--divider-color));
    overflow: hidden;
  }
  .thumb {
    aspect-ratio: 3 / 4;
    background: var(--secondary-background-color);
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }
  .thumb img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  .thumb .placeholder {
    padding: 12px;
    text-align: center;
    color: var(--cp-muted);
    font-size: 14px;
  }
  .wallpapers .thumb {
    aspect-ratio: 3 / 5;
  }
  .body {
    padding: 10px 12px 12px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    flex: 1;
  }
  .name {
    font-weight: 500;
    font-size: 14px;
    line-height: 1.3;
    overflow-wrap: anywhere;
  }
  .meta {
    color: var(--cp-muted);
    font-size: 13px;
  }
  .badge {
    align-self: flex-start;
    font-size: 12px;
    padding: 2px 8px;
    border-radius: 10px;
    background: var(--secondary-background-color);
    color: var(--cp-muted);
  }
  .badge.installed {
    color: var(--cp-ok);
  }
  .badge.modified {
    color: var(--cp-warn);
  }
  .badge.missing_from_library {
    color: var(--cp-error);
  }
  .progress {
    height: 4px;
    border-radius: 2px;
    background: var(--divider-color);
    overflow: hidden;
  }
  .progress div {
    height: 100%;
    background: var(--primary-color);
    transition: width 0.2s;
  }
  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: auto;
    padding-top: 4px;
  }
  button.action {
    font: inherit;
    font-size: 13px;
    font-weight: 500;
    padding: 6px 12px;
    border-radius: 16px;
    border: 1px solid var(--primary-color);
    background: var(--primary-color);
    color: var(--text-primary-color, #fff);
    cursor: pointer;
  }
  button.action.secondary {
    background: transparent;
    color: var(--primary-color);
  }
  button.action.danger {
    background: transparent;
    border-color: var(--cp-error);
    color: var(--cp-error);
  }
  button.action:disabled {
    opacity: 0.4;
    cursor: default;
  }
  button.action.toolbar-button {
    background: transparent;
    border-color: currentColor;
    color: inherit;
  }
  .segmented {
    display: inline-flex;
    border: 1px solid var(--divider-color);
    border-radius: 16px;
    overflow: hidden;
  }
  .segmented button {
    font: inherit;
    font-size: 12px;
    padding: 4px 10px;
    border: none;
    background: transparent;
    color: var(--cp-muted);
    cursor: pointer;
  }
  .segmented button[aria-pressed="true"] {
    background: var(--primary-color);
    color: var(--text-primary-color, #fff);
  }
  .empty {
    padding: 48px 16px;
    text-align: center;
    color: var(--cp-muted);
  }
  .scrim {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.45);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10;
    padding: 16px;
  }
  .dialog {
    background: var(--card-background-color);
    color: var(--primary-text-color);
    border-radius: var(--cp-radius);
    padding: 20px 24px 16px;
    max-width: 420px;
    width: 100%;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
  }
  .dialog h2 {
    margin: 0 0 8px;
    font-size: 18px;
    font-weight: 500;
  }
  .dialog p {
    margin: 0 0 16px;
    color: var(--cp-muted);
    line-height: 1.4;
  }
  .dialog .actions {
    justify-content: flex-end;
  }
  @media (max-width: 600px) {
    main {
      padding: 12px;
    }
    .grid {
      grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
      gap: 12px;
    }
    input[type="search"] {
      flex: 1;
      min-width: 0;
    }
  }
`;
