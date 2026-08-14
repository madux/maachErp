# Odoo Experience Africa 2026 - Landing Page

An Odoo 17 Community module that recreates the Odoo Experience Africa 2026
event landing page using QWeb (XML) templates, custom CSS, and a small
`publicWidget` JS module for interactions (mobile nav, scroll-reveal, chat
bubble hook).

## Install

1. Copy the `website_africa` folder into your Odoo
   `addons` path (alongside your other custom modules).
2. Restart the Odoo server (or just refresh Apps if `--dev=all` / autoreload
   is on).
3. Go to **Apps**, remove the "Apps" filter, search for
   **"Odoo Experience Africa 2026"**, and click **Install**.
4. Visit: `http://<your-odoo-url>/odoo-experience-africa`

The page is registered as a public, indexable website route (`auth='public'`,
`website=True`, `sitemap=True`), so it also shows up if you search the
website content.

## Files

```
website_africa/
├── __init__.py
├── __manifest__.py
├── controllers/
│   ├── __init__.py
│   └── main.py                 # exposes /odoo-experience-africa
├── views/
│   └── landing_templates.xml   # QWeb page template (all sections)
└── static/
    └── src/
        ├── css/landing.css     # dark "space" theme, cards, layout
        └── js/landing.js       # publicWidget: nav toggle, scroll reveal
```

## Replacing the placeholder images

Every image in `views/landing_templates.xml` currently points to a
`https://placehold.co/...` URL so the page renders out of the box without
any binary assets bundled in the module. To swap them for real photos:

1. Open `views/landing_templates.xml`.
2. Find the `<img src="https://placehold.co/...">` tag you want to change
   (they're labelled by `alt` text: mascot, speaker on stage, live
   performance, networking photo, each speaker headshot, the keynote photo,
   and the Kenya flag icon).
3. Replace the `src` with:
   - a URL to your own hosted image, **or**
   - a path to a static asset you add under
     `static/src/img/...` (e.g. `src="/website_africa/static/src/img/mascot.png"`),
     **or**
   - an Odoo-managed image field (e.g. `t-field` on a record) if you want
     it editable from the Website Builder.

No other file needs to change - the CSS/layout is written to accept any
image dimensions gracefully (it crops with `object-fit: cover` where
relevant).

## Customizing content (speakers, stats, sessions, apps)

All content (speaker names/titles, stat numbers, app list, dates, location)
is written directly in `views/landing_templates.xml` as plain HTML/QWeb -
edit the text there. Because it's a static XML view, Odoo Studio / Website
Builder "edit in place" won't manage it automatically, but you can:

- Edit the XML directly and upgrade the module (`-u website_africa`), or
- Convert sections into Website Builder-editable snippets later if you
  want marketers to edit copy without touching XML (let me know if you'd
  like that version).

## Notes

- Built and tested for **Odoo 17.0 Community**, depends only on the
  `website` module (no Enterprise dependencies).
- Header/footer of the base website theme are disabled on this page
  (`no_header` / `no_footer`) so the custom dark navbar/footer shown in the
  design fully control the page chrome. Remove those `t-set` lines in the
  template if you'd rather keep your site's standard header/footer.
