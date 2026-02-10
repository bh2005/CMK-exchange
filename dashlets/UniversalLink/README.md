
# Link / Button Dashlet – Quick Start Guide

## 📦 What is it?

A **universal link dashlet** for Checkmk that lets you:

✅ Create links to **other dashboards**  
✅ Create links to **Checkmk views** (hosts, services, problems, …)  
✅ Create links to **external URLs** (Grafana, NetBox, Zabbix, etc.)  
✅ **Embed iframes** (show other websites directly inside the dashboard)  
✅ Choose from different **display styles** (button, card, minimal, badge/tag)  
✅ Customize **icons** and **colors**

## 🚀 Installation

```bash
# As site user
sudo cp link_dashlet.py /omd/sites/SITE/local/share/check_mk/web/plugins/dashboard/
sudo chown SITE:SITE /omd/sites/SITE/local/share/check_mk/web/plugins/dashboard/link_dashlet.py
omd reload apache
```

Afterwards refresh your browser with:  
`Ctrl + Shift + R` (hard refresh)

## 🎯 Usage Examples

### Example 1: Link to another dashboard

**Use case:** Link from “Main Dashboard” to “Extreme AP Dashboard”

```
Link Type:          Internal Dashboard
  Dashboard Name:   extreme_ap_dashboard
Title:              Access Points Overview
Icon:               📡
Style:              Large Button
Background:         Gradient Blue
```

**Result:** Large blue button with 📡 icon

---

### Example 2: Link to Grafana

**Use case:** Direct link to a Grafana dashboard

```
Link Type:          External URL
  URL:              https://grafana.company.com/d/abc123/network
  Open in:          New window/tab
Title:              Grafana Network Dashboard
Description:        Network Performance Metrics
Icon:               📈
Style:              Card with shadow
Background:         Gradient Green
```

**Result:** Nice card that opens Grafana in a new tab

---

### Example 3: Embedded Grafana panel

**Use case:** Show a single Grafana panel directly inside the dashboard

```
Link Type:          Embedded iframe
  URL:              https://grafana.company.com/d-solo/abc123/network?panelId=2
Title:              (not relevant for iframes)
```

**Dashlet size:** Width: 40, Height: 30

**Result:** Grafana panel embedded seamlessly in the dashboard

---

### Example 4: Link to a Checkmk view

**Use case:** Quick access to “All Services” view

```
Link Type:          Internal View
  View Name:        allservices
Title:              All Services
Icon:               📋
Style:              Badge/Tag
Background:         Orange
```

**Result:** Small, compact badge-style button

---

### Example 5: Links to multiple external tools

**Use case:** Quick shortcuts to different admin tools

**Dashlet 1:**
```
URL:          https://netbox.company.com
Title:        NetBox IPAM
Icon:         🌐
Style:        Minimal link
```

**Dashlet 2:**
```
URL:          https://zabbix.company.com
Title:        Zabbix Monitoring
Icon:         🖥️
Style:        Minimal link
```

**Layout:** Place both next to each other as small links

## 🎨 Configuration Options

### Link Type

| Option                | Used for                              | Expected value          |
|-----------------------|---------------------------------------|--------------------------|
| **Internal Dashboard**| Other Checkmk dashboards              | `dashboard_name`        |
| **Internal View**     | Checkmk views (hosts, services, …)    | `view_name`             |
| **External URL**      | Any external website                  | `https://…`             |
| **Embedded iframe**   | Embed webpages inside the dashlet     | `https://…`             |

### Display Styles

| Style               | Appearance                     | Best used for                     |
|---------------------|--------------------------------|-----------------------------------|
| **Large Button**    | Big centered button            | Main navigation items             |
| **Card with shadow**| Card look with drop shadow     | Clean, modern overview links      |
| **Minimal link**    | Simple text link               | Many links side by side           |
| **Badge/Tag**       | Small pill-shaped badge        | Compact navigation                |

### Icons (Emoji selection)

- 📊 Chart / Dashboard  
- 🖥️ Server / Computer  
- 📈 Graph / Trending  
- 🔍 Search / View  
- ⚙️ Settings  
- 📱 Mobile / Device  
- 🌐 Network / Globe  
- 📡 Signal / Wireless  
- 🚀 Rocket / Launch  
- ⚡ Lightning / Fast  
- 🎯 Target / Focus  
- 📋 List / Document  
- 🔔 Notification  
- 👥 Users / Team  
- 🏢 Building

### Colors

**Background:**
- Solid: Blue, Green, Purple, Orange, Red, Gray
- Gradient: Blue, Green, Purple, Orange

**Text:**
- White, Black, Gray

## 📐 Layout Examples

### Layout 1 – Navigation Bar

```
┌─────────┬─────────┬─────────┬─────────┐
│ APs 📡  │ Grafana │ NetBox  │ Zabbix  │
│ (10×5)  │ (10×5)  │ (10×5)  │ (10×5)  │
└─────────┴─────────┴─────────┴─────────┘
```

Style: Badge/Tag or Minimal  
Size: 10×5 each

---

### Layout 2 – Main Navigation

```
┌──────────────────┬──────────────────┐
│ Access Points    │ Switches         │
│ 📡               │ 🌐               │
│ (20×10)          │ (20×10)          │
├──────────────────┼──────────────────┤
│ Grafana          │ NetBox           │
│ 📈               │ 🏢               │
│ (20×10)          │ (20×10)          │
└──────────────────┴──────────────────┘
```

Style: Large Button  
Size: 20×10 each

---

### Layout 3 – Embedded Tools

```
┌─────────────────────────────────────┐
│ [Link Buttons Row – 5× each]        │
│ APs | Grafana | NetBox | Zabbix     │
├─────────────────────────────────────┤
│ Embedded Grafana Dashboard          │
│ (iframe 60×40)                      │
└─────────────────────────────────────┘
```

Top: 4× Badge dashlets (total width ~60×5)  
Bottom: 1× large iframe dashlet (60×40)

---

### Layout 4 – Mixed Dashboard

```
┌──────────────┬──────────────────────┐
│ Extreme AP   │                      │
│ Statistics   │ Grafana iframe       │
│ (20×30)      │ (40×30)              │
├──────────────┼──────────────────────┤
│ Link: NetBox │ Link: Other Tools    │
│ (20×10)      │ (40×10)              │
└──────────────┴──────────────────────┘
```

## 🔧 Common Use Cases

1. **Navigation hub**  
   One dashboard linking to: Access Points • Switches • Servers • Network • Storage

2. **External tool integration**  
   Quick links to: Grafana • NetBox • Zabbix/Nagios • ServiceNow • Wiki/Confluence

3. **Embedded views**  
   Inline Grafana panels, weather maps, custom HTML status pages

4. **Quick actions / shortcuts**  
   Small badges linking to: Acknowledge problems • Service discovery • Host config • Reports

## 🎯 Step-by-step: Create your first link

1. Open dashboard  
   `Customize → Visualization → Dashboards → [your dashboard]`

2. Add dashlet  
   `Edit dashboard → Add dashlet → "Link / Button Dashlet"`

3. Configure

   **Basic**
   ```
   Title: Access Points
   ```

   **Link Type**
   ```
   ○ Internal Dashboard
     Dashboard Name: extreme_ap_dashboard
   ```

   **Appearance**
   ```
   Style:          Large Button
   Icon:           📡
   Background:     Gradient Blue
   Text Color:     White
   ```

   **Size**
   ```
   Width:  20
   Height: 10
   ```

4. Save & test  
   Click the button → should navigate to the target dashboard

## 💡 Pro Tips

### Tip 1: Finding dashboard names

Look at the URL:  
`https://checkmk.company.com/SITE/check_mk/dashboard.py?name=extreme_ap_dashboard`  
→ name = `extreme_ap_dashboard`

Or: Properties → ID

### Tip 2: Finding view names

URL pattern: `view.py?view_name=allservices` → `allservices`

Common ones:
- `allhosts`  
- `allservices`  
- `svcproblems`  
- `hostproblems`

### Tip 3: Good iframe sizes

- Small panel:   20×15  
- Medium panel:  40×30  
- Large panel:   60×40  
- Almost full:   80×60

### Tip 4: Grafana solo panel URL (for iframe)

Use the **solo** link:  
`https://grafana.company.com/d-solo/abc123/network?orgId=1&panelId=2`

Panel → Share → Link → “Direct link rendered image”

### Tip 5: Group many links

Create a grid:
- Same size (e.g. 15×8)  
- Same style (e.g. Card)  
- Different background colors per category

## 🔒 iframe Security Note

**⚠️ Important:** Not every website allows embedding via iframe!

**Usually works:**
- Internal tools  
- Grafana (with correct settings)  
- Self-hosted dashboards

**Usually blocked (X-Frame-Options):**
- Google, YouTube  
- Facebook, Twitter/X  
- GitHub  
- Most public SaaS platforms

**Workaround:** Use “External URL” + “Open in new tab/window” instead

## 📝 Checklist

- [ ] Dashlet file copied  
- [ ] File permissions correct  
- [ ] Apache reloaded  
- [ ] Dashboard opened  
- [ ] Dashlet added  
- [ ] Link type selected  
- [ ] Target configured  
- [ ] Title & icon set  
- [ ] Style & colors chosen  
- [ ] Size adjusted  
- [ ] Tested – link works

## 🎉 Done!

You can now:

- ✅ Link to other Checkmk dashboards  
- ✅ Link to external tools  
- ✅ Embed iframes (where allowed)  
- ✅ Build beautiful navigation buttons  
- ✅ Create complex dashboard layouts

**Popular next steps:**

- 🎨 Central navigation dashboard  
- 🚀 Quick-access toolbar  
- 📊 Hybrid Checkmk + Grafana dashboard  
- 🔗 Admin tool overview

Happy dashboard building! 🚀
