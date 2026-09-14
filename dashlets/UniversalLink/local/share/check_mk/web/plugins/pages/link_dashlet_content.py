#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# CMK 2.5: Iframe content page for LinkDashlet.
# Renders a styled button/card/minimal link — no CMK header.
#
# URL parameters (all optional, defaults shown):
#   title     – "Link"
#   icon      – ""  (emoji, e.g. 📊)
#   color     – blue|green|purple|orange|red  (default: blue)
#   style     – button|card|minimal           (default: button)
#   link_url  – "#"   target URL (URL-encoded)
#   target    – _top|_blank|_self             (default: _top)

from cmk.gui.htmllib.html import html
from cmk.gui.utils.html import HTML
from cmk.gui.pages import Page, PageEndpoint, PageContext, PageResult, page_registry

_COLOR_MAP = {
    "blue":   ("667eea", "764ba2"),
    "green":  ("11998e", "38ef7d"),
    "purple": ("a8edea", "fed6e3"),
    "orange": ("f093fb", "f5576c"),
    "red":    ("fa709a", "fee140"),
}


class LinkDashletContentPage(Page):
    def page(self, ctx: PageContext) -> PageResult:
        request = ctx.request
        title    = request.get_str_input("title")    or "Link"
        icon     = request.get_str_input("icon")     or ""
        color    = request.get_str_input("color")    or "blue"
        style    = request.get_str_input("style")    or "button"
        link_url = request.get_str_input("link_url") or "#"
        target   = request.get_str_input("target")   or "_top"

        c1, c2 = _COLOR_MAP.get(color, _COLOR_MAP["blue"])

        css = f"""
body{{margin:0;padding:0;font-family:inherit;overflow:hidden;}}
.wrapper{{height:100vh;display:flex;align-items:center;justify-content:center;padding:20px;box-sizing:border-box;}}
a{{text-decoration:none;color:white;display:flex;flex-direction:column;align-items:center;
   justify-content:center;width:100%;height:100%;border-radius:12px;
   background:linear-gradient(135deg,#{c1} 0%,#{c2} 100%);
   transition:all .3s ease;box-sizing:border-box;text-align:center;}}
a:hover{{transform:translateY(-6px);box-shadow:0 12px 25px rgba(0,0,0,.25);}}
.icon{{font-size:48px;margin-bottom:12px;}}
.title{{font-weight:bold;margin-bottom:6px;}}
.style-button a{{padding:30px;font-size:22px;box-shadow:0 8px 20px rgba(0,0,0,.2);}}
.style-button .title{{font-size:24px;}}
.style-button .icon{{font-size:60px;}}
.style-card a{{padding:20px;box-shadow:0 6px 15px rgba(0,0,0,.15);border:1px solid rgba(255,255,255,.2);}}
.style-card .title{{font-size:20px;}}
.style-card .icon{{font-size:50px;}}
.style-minimal a{{background:none!important;color:#333!important;padding:10px;border-radius:8px;}}
.style-minimal a:hover{{background:rgba(0,0,0,.05)!important;transform:none;box-shadow:none;}}
.style-minimal .icon{{font-size:32px;margin-bottom:8px;}}
.style-minimal .title{{font-size:16px;color:#333;}}
"""

        icon_html = f'<span class="icon">{icon}</span>' if icon else ""
        escaped_url = html.attrencode(link_url)

        full_html = (
            f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>{css}</style></head>"
            f"<body>"
            f'<div class="wrapper style-{style}">'
            f'<a href="{escaped_url}" target="{target}">'
            f'{icon_html}'
            f'<span class="title">{html.attrencode(title)}</span>'
            f"</a>"
            f"</div>"
            f"</body></html>"
        )
        html.write_html(HTML(full_html))
        return None


page_registry.register(PageEndpoint("link_dashlet_content", LinkDashletContentPage()))
