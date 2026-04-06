/**
 * Einstein Browser Extension — Content Script
 *
 * Runs on every page to provide page metadata and selected text
 * to the background service worker on request.
 */

(() => {
  "use strict";

  /**
   * Extract the content of a <meta> tag by name or property.
   *
   * @param {string} attr - The attribute key ("name" or "property").
   * @param {string} value - The attribute value to match (e.g. "description").
   * @returns {string} The content attribute value, or empty string.
   */
  function getMetaContent(attr, value) {
    const el = document.querySelector(`meta[${attr}="${value}"]`);
    return el ? el.getAttribute("content") || "" : "";
  }

  /**
   * Get the canonical URL for the page, if declared.
   *
   * @returns {string} The canonical URL, or empty string.
   */
  function getCanonicalUrl() {
    const link = document.querySelector('link[rel="canonical"]');
    return link ? link.getAttribute("href") || "" : "";
  }

  /**
   * Gather all relevant page metadata.
   *
   * @returns {object} Page data including selected text, title, description, and canonical URL.
   */
  function collectPageData() {
    return {
      selectedText: window.getSelection().toString(),
      title: document.title || "",
      description:
        getMetaContent("name", "description") ||
        getMetaContent("property", "og:description") ||
        "",
      canonicalUrl: getCanonicalUrl() || window.location.href,
    };
  }

  // Listen for requests from the background service worker.
  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message && message.action === "getPageData") {
      sendResponse(collectPageData());
    }
    // Return false — we respond synchronously.
    return false;
  });
})();
