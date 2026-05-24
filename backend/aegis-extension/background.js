/**
 * AEGIS Guard — Service worker. Icon states only.
 */

const ICONS = {
  grey: { 16: "icons/icon16.png", 48: "icons/icon48.png" },
  green: { 16: "icons/icon-green16.png", 48: "icons/icon-green48.png" },
  red: { 16: "icons/icon-red16.png", 48: "icons/icon-red48.png" },
  yellow: { 16: "icons/icon-yellow16.png", 48: "icons/icon-yellow48.png" },
  orange: { 16: "icons/icon-orange16.png", 48: "icons/icon-orange48.png" },
};

chrome.commands?.onCommand?.addListener((cmd) => {
  if (cmd === "reanalyze") {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]?.id) chrome.tabs.sendMessage(tabs[0].id, { type: "REANALYZE" }).catch(() => {});
    });
  }
});

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "NOTIFY_BLOCK") {
    const types = (msg.types || []).join(", ");
    chrome.notifications.create({
      type: "basic",
      iconUrl: "icons/icon-red48.png",
      title: "AEGIS Guard",
      message: "Blocked: " + (types || "Sensitive data") + " detected",
    });
    sendResponse({ ok: true });
    return true;
  }
  if (msg.type === "SET_ICON") {
    const icons = ICONS[msg.status] || ICONS.grey;
    chrome.action.setIcon({ path: icons })
      .then(() => sendResponse({ ok: true }))
      .catch(() => sendResponse({ ok: false }));
    return true;
  }
});
