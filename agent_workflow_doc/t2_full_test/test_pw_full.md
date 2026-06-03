# Walkthrough - microSchedule Full System QA

This document presents the execution walkthrough and validation results of the Tier 2 Full System QA suite run on the `microSchedule` application.

## Run Context
- **Run ID**: `FULLQA_20260603_183147`
- **Execution Date**: 2026-06-03
- **App URL**: `http://127.0.0.1:8550`
- **Status**: **ALL TESTS PASSED** (23/23 cases)

---

## Validation Results

Below is the summary of all executed test cases from the latest run:

| Test Case | Description | Status | Reason / Detail |
|---|---|---|---|
| **TC30** | Viewport configuration (1280x900) | `PASS` | Set viewport dimensions successfully. |
| **TC01** | App loads at localhost | `PASS` | Accessibility placeholder clicked, loaded without tracebacks. |
| **TC02** | Tabs render | `PASS` | Day, Month, and Notes tabs verified visible. |
| **TC03** | Settings dialog | `PASS` | Settings button clicked, verified dialog elements, closed successfully. |
| **TC04** | Reload page | `PASS` | Reloaded successfully, re-enabled accessibility. |
| **TC05** | Month View starts at current month/year | `PASS` | Month title matched expectation. |
| **TC06** | Main date cell click | `PASS` | Clicked current date, navigated to Day Detail tab correctly. |
| **TC07** | Click "Hôm nay" button | `PASS` | Button is responsive and verified clickable. |
| **TC08** | Mini Calendar date cell navigation | `PASS` | Successfully selected dates via mini calendar. |
| **TC09** | Mini Calendar chevron arrows | `PASS` | Navigated backwards and forwards between months. |
| **TC10** | Source Visibility Checkbox Toggle | `PASS` | Calendar source checkbox clicked and state updated. |
| **TC11** | Refresh Icon Click | `PASS` | Event list refreshed successfully without locking layout. |
| **TC14** | Day Detail Column / Task layout | `PASS` | Elements verified, including fixed calendar lists. |
| **TC15** | Day Navigation Arrows | `PASS` | Navigated between preceding and succeeding days. |
| **TC16** | Day VỀ HÔM NAY | `PASS` | Navigation reset back to current date successfully. |
| **TC17** | Task Mutation | `PASS` | Task created, edited, checked/unchecked, and deleted successfully. |
| **TC19** | Notes rendering & sort dropdown | `PASS` | Checked presence of textboxes and action buttons. |
| **TC20** | Quick Add Note | `PASS` | Input title, saved, and verified quick note card appearance. |
| **TC21** | Note dialog | `PASS` | Created note with checkboxes/details, saved successfully. |
| **TC22** | Note Pin, Archive, & Delete | `PASS` | Pinned note, archived it, scrolled list to locate, deleted, and cleaned up. |
| **TC23** | Sort option check | `PASS` | Toggled Title and Edit date sorting. |
| **TC25** | ICS File Import | `PASS` | File dialog uploaded fixture `LichThi-QLDT-20252.ics` successfully. |
| **TC26** | XLSX File Import | `PASS` | File dialog uploaded fixture `LichThi.xlsx` successfully. |

---

## Database Integrity & Safety

- **PostgreSQL Restore Status**: `SUCCESS`
- **SQLite Restore Status**: `SUCCESS`

> [!NOTE]
> Database integrity has been fully verified. A complete database backup of the PostgreSQL database (`microschedule_v2`) and SQLite database was taken before executing any mutations. After the test suite concluded, the `pg_restore` and file restoration procedures reverted the database states exactly to their pre-test snapshotted states.

---

## Visual Verification

Below are key screenshots highlighting the major steps in the automated QA execution flow:

### 1. App Startup (TC01)
Visual proof that the initial app loads fully with the navigation sidebar and month calendar layout.
![App Startup](/C:/Users/os/.gemini/antigravity/brain/cb9cb892-9e17-466b-bd5e-af3f83f107f7/qa_screenshots/01_startup.png)

### 2. Settings Dialog (TC03)
Visual confirmation of the settings menu drawer overlay.
![Settings Dialog](/C:/Users/os/.gemini/antigravity/brain/cb9cb892-9e17-466b-bd5e-af3f83f107f7/qa_screenshots/03_settings_dialog.png)

### 3. Task Mutation (TC17)
Shows the task created on the Day Detail page before compilation/editing steps.
![Task Mutation](/C:/Users/os/.gemini/antigravity/brain/cb9cb892-9e17-466b-bd5e-af3f83f107f7/qa_screenshots/06_task_saved.png)

### 4. Notes & Checklists (TC20)
Visual check demonstrating successful creation of a quick note.
![Notes and Checklists](/C:/Users/os/.gemini/antigravity/brain/cb9cb892-9e17-466b-bd5e-af3f83f107f7/qa_screenshots/07_quick_note_added.png)

### 5. Final Calendar State (TC26)
Month calendar view containing all imported fixture items from ICS and XLSX files prior to the database restore operation.
![Final Calendar State](/C:/Users/os/.gemini/antigravity/brain/cb9cb892-9e17-466b-bd5e-af3f83f107f7/qa_screenshots/09_final_calendar_view.png)
