# Screenshots for the README

Put the images in `docs/screenshots/` and hand them to Moh, who owns the README text.

## Shot list

Take them at a browser width of about 1280 px, zoom 100%, light mode unless noted.

| File | Page | What should be visible |
|---|---|---|
| `01-landing.png` | `/` logged out | Hero text and the three feature cards |
| `02-login.png` | `/accounts/login/` | The centered login card |
| `03-dashboard.png` | dashboard | Four stat cards, overdue list, due this week |
| `04-projects.png` | `/projects/` | Project cards with progress bars |
| `05-project-detail.png` | one project, with a filter applied | Filter bar and task rows |
| `06-task-detail.png` | one task with comments | Pills, description, comments |
| `07-staff-overview.png` | `/manage/` | Staff badge, tabs, five stat cards |
| `08-staff-users.png` | `/manage/users/` | Users table with Activate/Deactivate |
| `09-staff-activity.png` | `/manage/activity/` | Log table with a filter applied |
| `10-dark-mode.png` | dashboard in dark mode | Same page, theme toggled |
| `11-mobile.png` | project detail on a phone-width window | Hamburger menu and the + button |

## How to take them (Windows)

- Press `Win + Shift + S`, drag over the page, then paste into Paint and save as PNG.
- For the mobile shot: press `F12`, then `Ctrl + Shift + M` for the device toolbar, and pick a phone size.
- Log in as the demo account that has the seed data, so the pages are full.
- Until the real seed data is loaded, you can shoot from the preview at `http://127.0.0.1:8001/`.
  The look is identical.

## Snippet for the README

```markdown
## Screenshots

| Dashboard | Project detail |
|---|---|
| ![Dashboard](docs/screenshots/03-dashboard.png) | ![Project detail](docs/screenshots/05-project-detail.png) |

| Staff panel | Dark mode |
|---|---|
| ![Staff overview](docs/screenshots/07-staff-overview.png) | ![Dark mode](docs/screenshots/10-dark-mode.png) |
```
