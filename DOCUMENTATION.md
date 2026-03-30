# LeadGen CRM — Documentation

LeadGen CRM is an automated lead discovery and management platform designed to streamline the process of finding, tracking, and converting business prospects. This document provides a detailed overview of the current system architecture, features, and design.

---

## 🚀 Technical Stack

The application is built using a modern, efficient, and high-performance stack:

*   **Backend**: [FastAPI](https://fastapi.tiangolo.com/) (Python) — A high-performance, asynchronous web framework.
*   **Database**: [SQLAlchemy](https://www.sqlalchemy.org/) (Async) with SQLite (Current Developer Environment).
*   **Frontend**:
    *   **HTMX**: Used for "Interactivity without the JS Bloat." It handles partial page updates (like loading the leads table or dashboard KPIs) without full page reloads.
    *   **Tailwind CSS (v3)**: A utility-first CSS framework for rapid and highly customized styling.
    *   **Jinja2**: Server-side templating for rendering HTML with dynamic Python data.
    *   **Lucide Icons**: A beautiful, consistent open-source icon library.
*   **Deployment/Ops**:
    *   **Node.js/NPM**: Manages the Tailwind CSS CLI build process.
    *   **Concurrently**: Used to run the backend and CSS watcher in a single terminal command.

---

## 🎨 Design System & Aesthetics

The UI follows a premium, professional "Minimalist-Modern" aesthetic using a custom-developed color palette:

### **Color Palette (Space Indigo & Dusty Grape)**
| Color | Hex Code | Usage |
| :--- | :--- | :--- |
| **Space Indigo** | `#22223B` | Primary headings, dark text, active state icons. |
| **Dusty Grape** | `#4A4E69` | Primary buttons (`.btn-primary`), sidebar active links. |
| **Lilac Ash** | `#9A8C98` | Secondary icons, sub-headers, meta-text. |
| **Almond Silk** | `#C9ADA7` | Borders, table separators, subtle outlines. |
| **Seashell** | `#F2E9E4` | Application background, input fields, soft containers. |

### **UI Highlights**
*   **Sidebar Layout**: A fixed, always-accessible navigation menu with interactive hover effects and clear active states.
*   **Dynamic Hover States**: Icons and text automatically shift colors on hover to ensure maximum readability and a premium "alive" feel.
*   **Responsive Cards**: All information is organized into cards with soft borders, consistent padding, and elegant spacing.

---

## 🛠 Core Features

### 1. **Executive Dashboard**
The dashboard provides a high-level overview of the sales funnel:
*   **Real-time KPIs**: New Leads Today, Total Leads, Active Pipelines, and Closed Deals.
*   **Lead Stage Breakdown**: A visual summary of how leads are distributed across the pipeline (New, Contacted, Interested, etc.).
*   **Recent Activity**: A quick-view list of the latest leads discovered by the automated engine.

### 2. **Lead Management (Leads Page)**
The central hub for tracking and managing prospects:
*   **Smart Filtering**: Instantly filter leads by Status, City, or Pipeline source using asynchronous HTMX requests.
*   **Modern Data Table**: A highly readable table that perfectly aligns company details, ratings, and status badges.
*   **Lead Detail Drawer**: Clicking any lead opens a slide-out drawer (without refreshing the page) that contains full details, status controls, and a notes timeline.

### 3. **Automated Pipelines**
The "Engine" of the application:
*   Allows users to create automated lead discovery jobs (e.g., "Find Web Development companies in Pune").
*   Integrates with a scraper (Playwright/BeautifulSoup) to find and deduplicate leads automatically.

### 4. **Activity & Notes**
*   **Internal Notes**: Add and view a history of communication for every lead.
*   **Change Log**: The system automatically tracks status changes and updates as "Activities" to provide a full audit trail.

---

## 📁 Project Structure

```text
leadgen/
├── backend/
│   ├── app/                # Python code (FastAPI)
│   │   ├── core/           # Database config, Celery, Global Security
│   │   ├── models/         # SQLAlchemy Database models
│   │   ├── schemas/        # Pydantic data validation schemas
│   │   └── routers/        # API Endpoints (Leads, Pipelines, etc.)
│   ├── static/             # Static assets
│   │   └── css/            # Compiled Tailwind CSS (output.css)
│   ├── templates/          # Jinja2 HTML Templates
│   └── main.py             # App entry point
├── tailwind.config.js      # Tailwind UI Theme configuration
├── package.json            # NPM scripts and dev dependencies
└── requirements.txt        # Python dependencies
```

---

## ⚙️ Development Guide

### **Standard Development Shortcut**
To start the entire application (Backend + Tailwind Watcher) in one go:
```bash
npm run dev
```

### **Individual Commands**
*   **Tailwind Watcher**: `npm run watch:css` (Rebuilds CSS instantly as you edit HTML).
*   **FastAPI Backend**: `cd backend && uvicorn app.main:app --reload`.
*   **Build CSS for Prod**: `npm run build:css`.

---
*Last Updated: March 06, 2026*
