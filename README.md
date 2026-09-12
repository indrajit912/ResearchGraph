# ResearchGraph

> **An interactive, crowdsourced D3.js web platform for visualizing and mapping global academic research collaborations.**

ResearchGraph is a production-quality Flask web application designed for visualizing and collaboratively maintaining a global research collaboration network. Originally inspired by a personal portfolio visualization, this standalone platform provides researchers with permanent, shareable, interactive D3.js network graphs representing their academic collaborations, while allowing for a fully explorable Global Master Network.

## 🌟 Core Philosophy

1. **Curated Vertices:** Identities (Researchers) are strictly controlled by the Admin team to prevent duplicates, enforce email uniqueness, and maintain data integrity.
2. **Crowdsourced Edges:** Any authenticated user can seamlessly contribute collaborations (`ESTABLISHED` or `ONGOING`) to the shared global graph.
3. **Layered Moderation:** A robust Role-Based Access Control (RBAC) system delegates edge-approval to Moderators, while destructive actions (like vertex deletion) are strictly reserved for Admins and Superadmins.

---

## 🛠 Architecture & Tech Stack

- **Backend:** Python, Flask (Application Factory Pattern)
- **Database:** PostgreSQL (Production) / SQLite (Local Dev)
- **ORM & Migrations:** Flask-SQLAlchemy, Flask-Migrate (Alembic)
- **Authentication:** Flask-Login, Flask-WTF, itsdangerous (Token generation)
- **Frontend:** HTML5, CSS3, Bootstrap 5, Select2 (Searchable UI)
- **Visualization:** D3.js v7 (Force-Directed Graph)
- **Email Service:** Custom Hermes API Integration

### Database Schema (Entity-Relationship)

- `User` (Many-to-Many with `Role`)
- `Researcher` (Master curated database of vertices)
- `ResearcherEmail` (One-to-Many from Researcher, enforcing global uniqueness)
- `Collaboration` (Undirected Edges linking two Researchers)
- `CollaborationReport` & `ResearcherCorrectionReport` (Moderation queue and deletion requests)
- `AuditLog` (Accountability tracking for graph changes)

---

## 🚀 Key Features

- **Interactive D3.js Visualizations:** Beautiful, physics-simulated network graphs with distinct visual markers for `Established` (solid) vs `Ongoing` (dashed) collaborations.
- **Global & Local Views:** Explore the massive interconnected global graph, or filter down to a specific researcher's personal network (up to 3 degrees of separation).
- **Advanced Admin Tooling:** Specialized "Draw Edges" tools utilizing Select2 dropdowns and unique URL slugs for resolving name collisions and easily drawing connections between arbitrary vertices.
- **Cascading Deletions:** Secure, constraint-aware deletion logic that safely cascades across edges, emails, and active moderation tickets to prevent database corruption.

---

## 💻 Installation & Local Development

### 1. Clone & Setup Virtual Environment
```bash
git clone <repository_url>
cd ResearchGraph
python -m venv .venv

# Windows
.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```
*(Note: For local Windows development, `psycopg2-binary` and `gunicorn` are disabled in requirements.txt. Enable them for production Linux deployments.)*

### 3. Environment Variables
Copy the example configuration:
```bash
cp .env.example .env
```
Edit `.env` to include your `SECRET_KEY`, Database URL, and `HERMES` API credentials.

### 4. Initialize Database
```bash
export FLASK_APP=run.py  # (On Windows use: set FLASK_APP=run.py or $env:FLASK_APP="run.py")
flask db upgrade
```

### 5. Create Superadmin
Securely bootstrap the first superadmin (no hardcoded passwords):
```bash
flask create-superadmin
```

### 6. Run the Application
```bash
flask run
```

---

## 🔒 Security Review

- **RBAC Authentication:** Route protection is authoritatively enforced on the backend via the `@requires_role` decorator. Front-end visibility masking is strictly a UX enhancement, not a security layer.
- **Undirected Edge Protection:** The database leverages a `CHECK (researcher_a_id < researcher_b_id)` constraint paired with a `UNIQUE(researcher_a_id, researcher_b_id)` constraint. This makes it impossible for race conditions to insert duplicate `A-B` and `B-A` relationships into the graph.
- **Secrets Management:** Environment variables are strictly parsed from `.env`. No credentials, database URIs, or Hermes API keys are hardcoded in the repository.
- **Account Protection:** Superadmin roles cannot be modified, downgraded, or deleted by standard `ADMIN` users.

## ⚡ Performance Review

- **Graph Traversal (BFS):** Rather than transmitting the entire global graph to the browser for individual profiles, the `/api/network/<slug>?depth=d` endpoint uses an optimized database-level Breadth-First Search. It traverses adjacent edges up to the required depth, guaranteeing $O(V+E)$ performance on the server side and maintaining a lightweight JSON payload.
- **Indexing:** Primary indexes exist on UUIDs, lookup slugs, edge source/targets, and user emails to guarantee rapid sub-millisecond lookup times even as the network scales to thousands of vertices.

---

## 🌐 Deployment (Render / Production)

1. Connect the repository to your Render Web Service.
2. Set the build command: `pip install -r requirements.txt` (Ensure `gunicorn` and `psycopg2-binary` are uncommented).
3. Set the start command: `gunicorn -w 4 -b 0.0.0.0:$PORT run:app`
4. Inject your `.env` variables into the Render environment variables dashboard.
5. In the Render deploy script, ensure database migrations run prior to booting Gunicorn: `flask db upgrade`.

© 2026 Indrajit Ghosh. All rights reserved.
