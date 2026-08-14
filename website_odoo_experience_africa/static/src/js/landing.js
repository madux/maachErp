/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

/**
 * Widget powering the Odoo Experience Africa 2026 landing page:
 * - mobile nav toggle
 * - scroll-reveal animation for cards/sections
 * - simple chat bubble click handler (placeholder for a real live-chat widget)
 */
publicWidget.registry.OxpAfricaLanding = publicWidget.Widget.extend({
    selector: "#oxp_africa",
    events: {
        "click .oxp-burger": "_onBurgerClick",
        "click .oxp-nav-links a": "_onNavLinkClick",
        "click .oxp-chat-bubble": "_onChatBubbleClick",
    },

    /**
     * @override
     */
    start() {
        this._setupScrollReveal();
        return this._super(...arguments);
    },

    /**
     * Toggle a simple mobile navigation state on the navbar.
     */
    _onBurgerClick(ev) {
        const navbar = this.el.querySelector(".oxp-navbar");
        navbar.classList.toggle("oxp-nav-open");
        const links = this.el.querySelector(".oxp-nav-links");
        if (links) {
            links.classList.toggle("d-none");
            links.classList.toggle("d-flex");
            links.classList.add("flex-column");
        }
    },

    /**
     * Smooth-scroll to in-page anchors.
     */
    _onNavLinkClick(ev) {
        const href = ev.currentTarget.getAttribute("href");
        if (href && href.startsWith("#")) {
            const target = this.el.querySelector(href);
            if (target) {
                ev.preventDefault();
                target.scrollIntoView({ behavior: "smooth", block: "start" });
            }
        }
    },

    /**
     * Placeholder chat bubble action - hook your live chat / support
     * widget here (e.g. website_livechat) if installed.
     */
    _onChatBubbleClick() {
        // eslint-disable-next-line no-console
        console.log("Odoo Experience Africa - chat bubble clicked. Hook your livechat widget here.");
    },

    /**
     * Reveal cards and section titles as they enter the viewport.
     */
    _setupScrollReveal() {
        const revealSelectors = [
            ".oxp-stat-card",
            ".oxp-photo-card",
            ".oxp-speaker-card",
            ".oxp-app-card",
            ".oxp-keynote-card",
            ".oxp-sessions-text",
            ".oxp-sessions-image",
        ];
        const elements = this.el.querySelectorAll(revealSelectors.join(","));
        elements.forEach((el) => el.classList.add("oxp-reveal"));

        if (!("IntersectionObserver" in window)) {
            elements.forEach((el) => el.classList.add("oxp-visible"));
            return;
        }

        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add("oxp-visible");
                        observer.unobserve(entry.target);
                    }
                });
            },
            { threshold: 0.15 }
        );

        elements.forEach((el) => observer.observe(el));
    },
});

export default publicWidget.registry.OxpAfricaLanding;
