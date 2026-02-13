#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ticket System Snapin for jbelkacemi's Checkmk Ticket System
KORRIGIERT: html.td() braucht immer content parameter!
"""

import sqlite3
import os
from pathlib import Path
from datetime import datetime

from cmk.gui.i18n import _
from cmk.gui.htmllib.html import html
from cmk.gui.sidebar._snapin import snapin_registry, SidebarSnapin


@snapin_registry.register
class TicketSystemSnapin(SidebarSnapin):
    
    @staticmethod
    def type_name():
        return "ticket_system"
    
    @classmethod
    def title(cls):
        return _("Ticket System")
    
    @classmethod
    def description(cls):
        return _("jbelkacemi Ticket System Statistics")
    
    @classmethod
    def refresh_regularly(cls):
        return True
    
    @classmethod
    def refresh_interval(cls):
        return 30
    
    def show(self):
        """Main render function"""
        
        html.open_div(style="padding: 10px;")
        
        # Clickable Header - Link zum Dashboard
        html.open_div(style="margin-bottom: 10px;")
        html.a(
            "🎫 Tickets",
            href="wato.py?mode=ticket_system",
            style="font-weight: bold; font-size: 14px; color: #0084c8; text-decoration: none; border-bottom: 2px solid #0084c8; display: block; padding-bottom: 5px;",
            title=_("Open Ticket Dashboard")
        )
        html.close_div()
        
        # Get database
        omd_root = os.getenv("OMD_ROOT", "")
        db_path = Path(omd_root) / "var/check_mk/ticket_system/tickets.db"
        
        if not db_path.exists():
            html.open_div(style="background: #fff3cd; padding: 8px; border-radius: 4px; font-size: 11px;")
            html.write_text(_("Database not found"))
            html.close_div()
            html.close_div()
            return
        
        # Query database
        try:
            conn = sqlite3.connect(str(db_path), timeout=5)
            cursor = conn.cursor()
            
            # Get status counts
            cursor.execute("SELECT status, COUNT(*) FROM tickets GROUP BY status")
            results = cursor.fetchall()
            
            # Get total
            cursor.execute("SELECT COUNT(*) FROM tickets")
            total_result = cursor.fetchone()
            total = total_result[0] if total_result else 0
            
            # Get recent (last 24h)
            cursor.execute("SELECT COUNT(*) FROM tickets WHERE datetime(created_at) >= datetime('now', '-1 day')")
            recent_result = cursor.fetchone()
            recent = recent_result[0] if recent_result else 0
            
            # Get priority breakdown for open tickets
            cursor.execute("""
                SELECT priority, COUNT(*) 
                FROM tickets 
                WHERE LOWER(status) = 'open' 
                GROUP BY priority
            """)
            priority_results = cursor.fetchall()
            
            conn.close()
            
            # Build stats dict
            stats = dict(results)
            priorities = dict(priority_results)
            
            # Main stats table
            html.open_table(style="width: 100%; font-size: 12px; margin-bottom: 8px;")
            
            # Open tickets (clickable)
            open_count = stats.get('open', 0)
            html.open_tr(style="cursor: pointer;", onclick="location.href='wato.py?mode=ticket_system&filter=open'")
            html.td("Open:", style="color: #666; padding: 4px 0;")
            html.td(
                str(open_count), 
                style="text-align: right; font-weight: bold; color: #28a745; padding: 4px 0;"
            )
            html.close_tr()
            
            # Show priority breakdown if there are open tickets
            if open_count > 0 and priorities:
                for priority, count in sorted(priorities.items(), key=lambda x: {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}.get(x[0].lower(), 99)):
                    priority_colors = {
                        'critical': '#dc3545',
                        'high': '#fd7e14',
                        'medium': '#ffc107',
                        'low': '#6c757d'
                    }
                    color = priority_colors.get(priority.lower(), '#999')
                    
                    html.open_tr(style="cursor: pointer;", onclick=f"location.href='wato.py?mode=ticket_system&priority={priority.lower()}'")
                    html.td(
                        f"  • {priority.capitalize()}:", 
                        style="color: #999; padding: 2px 0; font-size: 11px; padding-left: 10px;"
                    )
                    html.td(
                        str(count),
                        style=f"text-align: right; font-weight: bold; color: {color}; padding: 2px 0; font-size: 11px;"
                    )
                    html.close_tr()
            
            # Closed tickets (clickable)
            closed_count = stats.get('closed', 0)
            html.open_tr(style="cursor: pointer;", onclick="location.href='wato.py?mode=ticket_system&filter=closed'")
            html.td("Closed:", style="color: #666; padding: 4px 0;")
            html.td(
                str(closed_count), 
                style="text-align: right; color: #6c757d; padding: 4px 0;"
            )
            html.close_tr()
            
            # Separator - KORRIGIERT: td() braucht content!
            html.open_tr(style="border-top: 1px solid #ddd;")
            html.td("", style="padding: 2px 0;")  # Leerer String statt kein Parameter
            html.td("", style="padding: 2px 0;")  # Leerer String statt kein Parameter
            html.close_tr()
            
            # Total
            html.open_tr(style="cursor: pointer;", onclick="location.href='wato.py?mode=ticket_system'")
            html.td("Total:", style="font-weight: bold; padding: 4px 0;")
            html.td(
                str(total), 
                style="text-align: right; font-weight: bold; padding: 4px 0;"
            )
            html.close_tr()
            
            # Recent (last 24h)
            if recent > 0:
                html.open_tr()
                html.td(
                    "Last 24h:", 
                    style="color: #999; font-size: 10px; padding: 2px 0;"
                )
                html.td(
                    str(recent), 
                    style="text-align: right; color: #999; font-size: 10px; padding: 2px 0;"
                )
                html.close_tr()
            
            html.close_table()
            
            # Quick action link
            html.open_div(style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #eee;")
            html.a(
                "➕ " + _("Create Ticket"),
                href="wato.py?mode=ticket_system&action=create",
                style="font-size: 11px; color: #0084c8; text-decoration: none;",
                title=_("Create new ticket")
            )
            html.close_div()
            
        except Exception as e:
            html.open_div(style="background: #f8d7da; padding: 8px; border-radius: 4px; font-size: 11px;")
            html.write_text("Error: ")
            html.write_text(str(e))
            html.close_div()
        
        # Footer with timestamp
        html.open_div(style="margin-top: 8px; padding-top: 6px; border-top: 1px solid #eee; font-size: 9px; color: #999; text-align: right;")
        html.write_text(datetime.now().strftime('%H:%M:%S'))
        html.close_div()
        
        html.close_div()
