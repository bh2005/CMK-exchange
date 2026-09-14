#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# CMK 2.5: IFrameDashlet for Universal Link.
# show() is gone in CMK 2.5 — content rendered by link_dashlet_content.py.
#
# URL format for the dashlet:
#   ../check_mk/link_dashlet_content.py?title=MyLink&icon=📊&color=blue&style=button&link_url=dashboard.py%3Fname%3Dmain&target=_top
#
# Parameters:
#   title     – button label
#   icon      – emoji icon (optional)
#   color     – blue|green|purple|orange|red
#   style     – button|card|minimal
#   link_url  – target URL (URL-encoded)
#   target    – _top|_blank|_self  (use _top to navigate the parent window)

from cmk.gui.dashboard import dashlet_registry
from cmk.gui.dashboard.dashlet.base import IFrameDashlet, RelativeLayoutConstraints, WidgetSize
from cmk.gui.dashboard.type_defs import DashletConfig
from cmk.gui.i18n import _


class LinkDashletConfig(DashletConfig):
    url: str


class LinkDashlet(IFrameDashlet[LinkDashletConfig]):
    """Universal Link dashlet (CMK 2.5).

    Renders via IFrame. Point URL to link_dashlet_content.py with parameters.
    """

    @classmethod
    def type_name(cls) -> str:
        return "link_dashlet"

    @classmethod
    def title(cls) -> str:
        return _("Link / Button")

    @classmethod
    def description(cls) -> str:
        return _(
            "Clickable link or button to a dashboard, view, or URL. "
            "Set URL to: ../check_mk/link_dashlet_content.py?title=MyLink&color=blue&link_url=..."
        )

    @classmethod
    def sort_index(cls) -> int:
        return 10

    @classmethod
    def relative_layout_constraints(cls) -> RelativeLayoutConstraints:
        return RelativeLayoutConstraints(initial_size=WidgetSize(width=20, height=10))


dashlet_registry.register(LinkDashlet)
