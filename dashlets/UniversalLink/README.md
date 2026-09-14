
# Link / Button Dashlet – Quick Start Guide

## 📦 What is it?

A **universal link dashlet** for Checkmk 2.5 that renders a clickable
link/button/card to another dashboard, a Checkmk view, or an external URL,
inside a styled iframe.

> **CMK 2.5 rewrite:** Checkmk 2.5 removed the classic `Dashlet.show()` API
> that older dashlets (including earlier versions of this one) relied on.
> This version uses the `IFrameDashlet` API instead and renders its content
> via a small dedicated page (`link_dashlet_content.py`). As a side effect,
> the rich configuration dialog (dropdowns for icon/color/style/link type)
> from the pre-2.5 version is gone — for now, the target URL and its look
> are configured by hand as query parameters (see below).

## 🚀 Installation

Two files, in **two different locations** — don't skip either one:

```bash
# As site user
sudo cp local/lib/python3/cmk/gui/plugins/dashboard/link_dashlet.py \
        /omd/sites/SITE/local/lib/python3/cmk/gui/plugins/dashboard/link_dashlet.py

sudo cp local/share/check_mk/web/plugins/pages/link_dashlet_content.py \
        /omd/sites/SITE/local/share/check_mk/web/plugins/pages/link_dashlet_content.py

sudo chown -R SITE:SITE /omd/sites/SITE/local/lib/python3/cmk/gui/plugins/dashboard/link_dashlet.py \
                          /omd/sites/SITE/local/share/check_mk/web/plugins/pages/link_dashlet_content.py
omd reload apache
```

Or package both as one `.mkp` (part `gui`: `dashboard/link_dashlet.py`, part
`web`: `plugins/pages/link_dashlet_content.py`) and upload it via
**Setup → Maintenance → Extension packages → Upload package**.

Afterwards refresh your browser with `Ctrl + Shift + R` (hard refresh).

## 🎯 Usage

1. Open a dashboard → **Edit dashboard → Add dashlet → "Link / Button"**.
2. In the dashlet's URL/iframe field, point it at the content page with
   query parameters:

```
../check_mk/link_dashlet_content.py?title=MyLink&icon=📊&color=blue&style=button&link_url=dashboard.py%3Fname%3Dmain&target=_top
```

### Parameters

| Parameter  | Values                              | Default | Notes                                             |
|------------|--------------------------------------|---------|----------------------------------------------------|
| `title`    | any text                            | `Link`  | Button label                                        |
| `icon`     | any emoji                           | (none)  | Optional icon shown above the title                 |
| `color`    | `blue`\|`green`\|`purple`\|`orange`\|`red` | `blue`  | Gradient background                          |
| `style`    | `button`\|`card`\|`minimal`         | `button`| Visual style                                        |
| `link_url` | URL-encoded target URL              | `#`     | e.g. `dashboard.py%3Fname%3Dmain`, `view.py%3Fview_name%3Dallservices`, or a full external `https://…` |
| `target`   | `_top`\|`_blank`\|`_self`           | `_top`  | Use `_top` to navigate the parent window/tab out of the iframe |

### Examples

**Link to another dashboard:**
```
link_url=dashboard.py%3Fname%3Dextreme_ap_dashboard&title=Access%20Points&icon=📡&color=blue&target=_top
```

**Link to a Checkmk view:**
```
link_url=view.py%3Fview_name%3Dallservices&title=All%20Services&icon=📋&color=orange&target=_top
```

**Link to an external tool (new tab):**
```
link_url=https%3A%2F%2Fgrafana.company.com%2Fd%2Fabc123%2Fnetwork&title=Grafana&icon=📈&color=green&target=_blank
```

## 🎨 Available colors

`blue`, `green`, `purple`, `orange`, `red` — each a two-stop gradient, see
`link_dashlet_content.py` for the exact hex values.

## 🎨 Styles

- `button` – large centered button
- `card` – card with border/shadow
- `minimal` – plain text link, dark on transparent

## 🔒 Notes

- The dashlet always renders through an iframe (`link_dashlet_content.py`);
  there is no separate "embed external site directly" mode anymore — for an
  arbitrary external iframe, use Checkmk's built-in generic iframe dashlet
  instead.
- `target=_top` is required to make dashboard/view links actually navigate
  the outer Checkmk page instead of staying trapped inside the iframe.

## 📝 Checklist

- [ ] Both files copied to their site paths (`gui/plugins/dashboard` **and**
      `web/plugins/pages`)
- [ ] Apache reloaded
- [ ] Dashlet added to dashboard
- [ ] URL parameters configured, `target=_top` set for internal links
- [ ] Tested – link/button renders and navigates correctly
