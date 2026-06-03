# QA Verification Walkthrough - microSchedule

This walkthrough summarizes the QA automation execution and verification results for the `microSchedule` application. All tests were executed using a standalone Playwright script, capturing comprehensive execution evidence.

## Executive Summary

- **Run ID**: `MICROSCHEDULE_QA_20260603_170112`
- **Execution Date**: 2026-06-03
- **Test Status**: **PASSED** (8/8 Test Cases Successful)
- **Target Application**: Flet Python Web Application (`http://127.0.0.1:8550`)
- **Database State**: Fully restored to pre-test state.

---

## Test Results Summary

| ID | Test Case / Feature Checked | Status | Description |
|---|---|---|---|
| **TC-01** | Startup & Main Navigation | **PASS** | Validated Flet startup and verified `LỊCH THÁNG` is the default active tab. |
| **TC-02** | Calendar Date Click | **PASS** | Clicked main calendar cell for `03/06/2026` and verified automatic navigation to `CHI TIẾT NGÀY`. |
| **TC-03** | Calendar "Hôm nay" Navigation | **PASS** | Returned to `LỊCH THÁNG`, clicked `Hôm nay` button, and verified the calendar shifted correctly. |
| **TC-04** | Mini Calendar Date Cell Navigation | **PASS** | Clicked June 5 date cell in the mini calendar widget and verified calendar update. |
| **TC-05** | Source Visibility & Refresh Toggle | **PASS** | Toggled a calendar source checkbox and performed an offset mouse click to trigger the refresh icon. |
| **TC-06** | Day Detail Navigation & "VỀ HÔM NAY" | **PASS** | Navigated day detail view using navigation arrows and verified resetting via `VỀ HÔM NAY`. |
| **TC-07** | Notes CRUD Smoke Test | **PASS** | Verified full creation, checklist item addition, editing, and deletion of a note card. |
| **TC-08** | ICS and XLSX Import Regression | **PASS** | Tested file chooser dialogs to import `LichThi-QLDT-20252.ics` and `LichThi.xlsx` events. |

---

## Technical Implementations & Workarounds

During automation script construction, several key Flet accessibility quirks were handled:
1. **Accessibility Mode**: Dispatched an initial click on the `flt-semantics-placeholder` using JavaScript to force Flet's semantic elements to render in the DOM.
2. **Refresh Button Location**: Flet's refresh icon button lacks a label or accessible name. Implemented a mouse-offset click based on the bounding box of the adjacent `"Hôm nay"` button.
3. **Card Group Differentiation**: Modified selectors to query `[role="group"][aria-label*="[runId]_note"]` to target only the specific note Card containing our unique run timestamp rather than high-level container groups.
4. **Index-Based Button Interactions**: Targeted the note's action buttons (Edit at index `1`, Delete at index `3`) within the isolated note card semantics tree.

---

## Visual Evidence

### 1. Calendar & Navigation flow (TC-01 to TC-06)
````carousel
![Startup View](/C:/Users/os/.gemini/antigravity/brain/543b9baa-12f5-4c26-9ade-8920f735342d/qa_artifacts/01_startup.png)
<!-- slide -->
![Day Detail Opened](/C:/Users/os/.gemini/antigravity/brain/543b9baa-12f5-4c26-9ade-8920f735342d/qa_artifacts/02_day_detail_opened.png)
<!-- slide -->
![Hôm Nay Clicked](/C:/Users/os/.gemini/antigravity/brain/543b9baa-12f5-4c26-9ade-8920f735342d/qa_artifacts/03_hom_nay_clicked.png)
<!-- slide -->
![Mini Calendar June 5 Clicked](/C:/Users/os/.gemini/antigravity/brain/543b9baa-12f5-4c26-9ade-8920f735342d/qa_artifacts/04_mini_calendar_clicked.png)
<!-- slide -->
![Source Toggled and Refreshed](/C:/Users/os/.gemini/antigravity/brain/543b9baa-12f5-4c26-9ade-8920f735342d/qa_artifacts/05_source_toggled_refreshed.png)
<!-- slide -->
![Day Detail Return to Today](/C:/Users/os/.gemini/antigravity/brain/543b9baa-12f5-4c26-9ade-8920f735342d/qa_artifacts/06_ve_hom_nay.png)
````

### 2. Notes CRUD Smoke Flow (TC-07)
````carousel
![Notes Default View](/C:/Users/os/.gemini/antigravity/brain/543b9baa-12f5-4c26-9ade-8920f735342d/qa_artifacts/07_notes_view.png)
<!-- slide -->
![Add Note Dialog](/C:/Users/os/.gemini/antigravity/brain/543b9baa-12f5-4c26-9ade-8920f735342d/qa_artifacts/07_add_note_dialog.png)
<!-- slide -->
![Note Fields Filled](/C:/Users/os/.gemini/antigravity/brain/543b9baa-12f5-4c26-9ade-8920f735342d/qa_artifacts/07_note_dialog_filled.png)
<!-- slide -->
![Note Saved on Grid](/C:/Users/os/.gemini/antigravity/brain/543b9baa-12f5-4c26-9ade-8920f735342d/qa_artifacts/07_note_saved.png)
<!-- slide -->
![Edit Note Dialog](/C:/Users/os/.gemini/antigravity/brain/543b9baa-12f5-4c26-9ade-8920f735342d/qa_artifacts/07_note_dialog_edited.png)
<!-- slide -->
![Edited Note Saved](/C:/Users/os/.gemini/antigravity/brain/543b9baa-12f5-4c26-9ade-8920f735342d/qa_artifacts/07_note_edited_saved.png)
<!-- slide -->
![Delete Confirmation](/C:/Users/os/.gemini/antigravity/brain/543b9baa-12f5-4c26-9ade-8920f735342d/qa_artifacts/07_delete_confirm_dialog.png)
<!-- slide -->
![Note Deleted](/C:/Users/os/.gemini/antigravity/brain/543b9baa-12f5-4c26-9ade-8920f735342d/qa_artifacts/07_note_deleted.png)
````

### 3. File Imports & Final Render (TC-08)
````carousel
![ICS File Parsing Done](/C:/Users/os/.gemini/antigravity/brain/543b9baa-12f5-4c26-9ade-8920f735342d/qa_artifacts/08_import_ics_done.png)
<!-- slide -->
![XLSX File Parsing Done](/C:/Users/os/.gemini/antigravity/brain/543b9baa-12f5-4c26-9ade-8920f735342d/qa_artifacts/08_import_xlsx_done.png)
<!-- slide -->
![Final Calendar View](/C:/Users/os/.gemini/antigravity/brain/543b9baa-12f5-4c26-9ade-8920f735342d/qa_artifacts/09_final_calendar_view.png)
````

---

## Database Restoration & Safety Check

As required by safety specifications, all mutated data has been successfully reverted to its pre-test state.
- **SQLite Database** (`todo.db`): Restored from backup.
- **PostgreSQL Database**: Re-imported from `postgres.dump` via `pg_restore --clean --if-exists`.
- **Status**: **Verified Clean**.
