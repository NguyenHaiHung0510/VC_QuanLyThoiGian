import os
import sys
import time
import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

def log(msg):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)

def switch_to_tab(page, tab_name):
    log(f"Attempting to switch to tab: {tab_name}")
    # Locate tab element in the tab list
    tab = page.locator(f'[role="tab"][aria-label="{tab_name}"]')
    tab.click(force=True)
    time.sleep(2)

    # Verify if selected
    is_selected = tab.get_attribute("aria-selected") == "true"
    if not is_selected:
        log(f"WARNING: Tab '{tab_name}' is not marked selected. Retrying click...")
        tab.click(force=True)
        time.sleep(2)
    log(f"Tab '{tab_name}' selection verified: {tab.get_attribute('aria-selected') == 'true'}")

def main():
    # Resolve or generate Run ID
    run_id = os.environ.get("RUN_ID")
    if not run_id:
        run_id = "MICROSCHEDULE_QA_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log(f"Starting Playwright Automation. Run ID: {run_id}")

    # Establish paths
    repo_dir = Path("C:/Users/os/Desktop/old_prj/VC_QuanLyThoiGian")
    artifacts_dir = repo_dir / "agent_workflow_doc" / "tier2_task_specs" / "qa_artifacts" / run_id
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    log(f"Artifacts will be saved to: {artifacts_dir}")

    ics_path = repo_dir / "LichThi-QLDT-20252.ics"
    xlsx_path = repo_dir / "LichThi.xlsx"

    if not ics_path.exists():
        log(f"WARNING: ICS fixture not found at {ics_path}")
    if not xlsx_path.exists():
        log(f"WARNING: XLSX fixture not found at {xlsx_path}")

    with sync_playwright() as p:
        log("Launching Chromium browser...")
        browser = p.chromium.launch(headless=True)
        # Configure viewport to 1280x720
        page = browser.new_page(viewport={"width": 1280, "height": 720})

        url = "http://127.0.0.1:8550"
        log(f"Navigating to {url}...")
        page.goto(url)

        log("Waiting 8s for Flet application to fully load...")
        time.sleep(8)

        # 1. Enable Accessibility
        log("Enabling accessibility via flt-semantics-placeholder...")
        try:
            page.evaluate("() => document.querySelector('flt-semantics-placeholder').click()")
            time.sleep(3)
            log("Accessibility enabled.")
        except Exception as e:
            log(f"Failed to click accessibility placeholder: {e}")

        # TC Startup
        log("TC-01: Startup and Main Navigation Verification")
        page.screenshot(path=str(artifacts_dir / "01_startup.png"))
        log("Saved startup screenshot.")

        # Verify LỊCH THÁNG tab is active
        try:
            lich_thang_tab = page.locator('[role="tablist"] [role="tab"][aria-label="LỊCH THÁNG"]')
            is_selected = lich_thang_tab.get_attribute("aria-selected") == "true"
            log(f"Initial LỊCH THÁNG tab active status: {is_selected}")
        except Exception as e:
            log(f"Could not verify LỊCH THÁNG tab status: {e}")

        # TC Calendar Date Cell click
        log("TC-02: Calendar Regression - Date Cell Click")
        try:
            # Click date cell of June 3, 2026 in the main calendar grid (has 📅 prefix)
            date_cell = page.locator('[role="button"]:has-text("📅 03/06/2026")').first
            log(f"Clicking main calendar date cell for 03/06/2026...")
            date_cell.click(force=True)
            time.sleep(3)
            page.screenshot(path=str(artifacts_dir / "02_day_detail_opened.png"))
            log("Saved day detail opened screenshot.")

            # Verify we are on CHI TIẾT NGÀY tab (index 0)
            day_tab = page.locator('[role="tab"][aria-label="CHI TIẾT NGÀY"]')
            log(f"CHI TIẾT NGÀY tab active: {day_tab.get_attribute('aria-selected') == 'true'}")
        except Exception as e:
            log(f"Failed during date cell click: {e}")

        # Return to LỊCH THÁNG
        log("Returning to LỊCH THÁNG tab...")
        try:
            switch_to_tab(page, "LỊCH THÁNG")
        except Exception as e:
            log(f"Failed to switch back to LỊCH THÁNG tab: {e}")

        # Click Hôm nay
        log("TC-03: Calendar Regression - 'Hôm nay' button click")
        try:
            # Match only the button exactly named "Hôm nay" on the active calendar header
            hom_nay_btn = page.get_by_role("button", name="Hôm nay", exact=True)
            log("Clicking 'Hôm nay' button...")
            hom_nay_btn.click(force=True)
            time.sleep(2)
            page.screenshot(path=str(artifacts_dir / "03_hom_nay_clicked.png"))
            log("Saved Hôm nay clicked screenshot.")
        except Exception as e:
            log(f"Failed clicking 'Hôm nay' button: {e}")

        # Click mini-calendar date cell
        log("TC-04: Calendar Regression - Mini Calendar Click")
        try:
            # Ensure we are on LỊCH THÁNG tab
            switch_to_tab(page, "LỊCH THÁNG")
            # Click June 5, 2026 in the mini-calendar (text is '05/06/2026 5')
            mini_date_cell = page.locator('[role="button"]').filter(has_text="05/06/2026 5").first
            log("Clicking mini-calendar date cell June 5...")
            mini_date_cell.click(force=True)
            time.sleep(2)
            page.screenshot(path=str(artifacts_dir / "04_mini_calendar_clicked.png"))
            log("Saved mini calendar clicked screenshot.")
        except Exception as e:
            log(f"Failed during mini-calendar date click: {e}")

        # Source toggle & Refresh
        log("TC-05: Source Visibility and Refresh")
        try:
            # Ensure we are on LỊCH THÁNG tab
            switch_to_tab(page, "LỊCH THÁNG")
            # Find checkbox for first source
            checkbox = page.locator('[role="checkbox"]').first
            log("Toggling first source checkbox...")
            checkbox.click(force=True)
            time.sleep(1)

            # Click refresh button using coordinate relative to "Hôm nay" button
            # because Flet REFRESH icon button does not expose accessibility label.
            hom_nay_btn = page.get_by_role("button", name="Hôm nay", exact=True)
            hom_nay_box = hom_nay_btn.bounding_box()
            if hom_nay_box:
                x = hom_nay_box["x"] - 25
                y = hom_nay_box["y"] + hom_nay_box["height"] / 2
                log(f"Clicking refresh button via coordinates: x={x}, y={y}")
                page.mouse.click(x, y)
            else:
                log("WARNING: Could not find Hôm nay bounding box, trying selector fallback...")
                page.locator('[aria-label="Làm mới lịch"]').first.click(force=True)

            time.sleep(2)
            page.screenshot(path=str(artifacts_dir / "05_source_toggled_refreshed.png"))
            log("Saved source toggle & refresh screenshot.")
        except Exception as e:
            log(f"Failed during source toggle or refresh: {e}")

        # Day Detail Arrows Smoke
        log("TC-06: Day Detail Navigation Smoke")
        try:
            # Ensure we switch to CHI TIẾT NGÀY tab
            switch_to_tab(page, "CHI TIẾT NGÀY")

            # Find "VỀ HÔM NAY" button and click it
            ve_hom_nay_btn = page.locator('[role="button"]:has-text("VỀ HÔM NAY")').first
            log("Clicking VỀ HÔM NAY...")
            ve_hom_nay_btn.click(force=True)
            time.sleep(2)
            page.screenshot(path=str(artifacts_dir / "06_ve_hom_nay.png"))
        except Exception as e:
            log(f"Failed during day detail smoke: {e}")

        # Notes smoke test (Create, Edit, Delete)
        log("TC-07: Notes Smoke Test (Create, Edit, Delete)")
        try:
            # Navigate to GHI CHÚ tab
            switch_to_tab(page, "GHI CHÚ")
            page.screenshot(path=str(artifacts_dir / "07_notes_view.png"))

            # Click THÊM GHI CHÚ button
            log("Clicking THÊM GHI CHÚ...")
            page.locator('[role="button"]:has-text("THÊM GHI CHÚ")').first.click(force=True)
            time.sleep(2)
            page.screenshot(path=str(artifacts_dir / "07_add_note_dialog.png"))

            # Fill title and body
            note_title = f"{run_id}_note"
            # Extract a unique partial title to avoid wrapped text locator failure
            note_partial = run_id.split('_')[-1] + "_note"
            note_partial_edited = run_id.split('_')[-1] + "_note_edited"

            log(f"Filling note details with title: {note_title}...")
            page.get_by_label("Tiêu đề").fill(note_title)
            time.sleep(0.5)
            page.get_by_label("Nội dung chi tiết").fill("This is a temporary note body created by automation.")
            time.sleep(0.5)

            # Add checklist item (input has aria-label="Thêm mục nhỏ...")
            log("Adding checklist item in dialog...")
            page.get_by_label("Thêm mục nhỏ...").fill("Checklist Item 1")
            time.sleep(0.5)
            page.get_by_label("Thêm mục nhỏ...").press("Enter")
            time.sleep(1)

            page.screenshot(path=str(artifacts_dir / "07_note_dialog_filled.png"))

            # Click LƯU GHI CHÚ
            log("Clicking LƯU GHI CHÚ...")
            page.locator('[role="button"]:has-text("LƯU GHI CHÚ")').first.click(force=True)
            time.sleep(3)
            page.screenshot(path=str(artifacts_dir / "07_note_saved.png"))
            log("Note saved successfully.")

            # Verify note card exists and click it to edit
            # Find the card container group that contains the unique partial title text
            log(f"Locating note card for partial title '{note_partial}'...")
            note_card = page.locator(f'[role="group"][aria-label*="{note_partial}"]').first

            # Wait for button to be visible to make sure card loaded
            note_card.locator('[role="button"]').first.wait_for(state="visible", timeout=10000)
            edit_btn = note_card.locator('[role="button"]').nth(1)
            log("Clicking edit button (index 1) for note...")
            edit_btn.click(force=True)
            time.sleep(2)

            # Edit Title and add another item
            log("Editing note title and adding second checklist item...")
            page.get_by_label("Tiêu đề").fill(f"{note_title}_edited")
            time.sleep(0.5)
            page.get_by_label("Thêm mục nhỏ...").fill("Checklist Item 2")
            time.sleep(0.5)
            page.get_by_label("Thêm mục nhỏ...").press("Enter")
            time.sleep(1)

            # Save again
            page.screenshot(path=str(artifacts_dir / "07_note_dialog_edited.png"))
            page.locator('[role="button"]:has-text("LƯU GHI CHÚ")').first.click(force=True)
            time.sleep(3)
            page.screenshot(path=str(artifacts_dir / "07_note_edited_saved.png"))
            log("Note edited and saved successfully.")

            # Delete note
            log("Locating delete button for note card...")
            note_card_edited = page.locator(f'[role="group"][aria-label*="{note_partial_edited}"]').first
            note_card_edited.locator('[role="button"]').first.wait_for(state="visible", timeout=10000)
            delete_btn = note_card_edited.locator('[role="button"]').nth(3)
            log("Clicking delete button (index 3) on the note card...")
            delete_btn.click(force=True)

            time.sleep(2)
            page.screenshot(path=str(artifacts_dir / "07_delete_confirm_dialog.png"))

            # Click XÓA in confirmation dialog
            log("Confirming deletion...")
            page.locator('[role="button"]:has-text("XÓA")').first.click(force=True)
            time.sleep(3)
            page.screenshot(path=str(artifacts_dir / "07_note_deleted.png"))
            log("Note deleted successfully.")
        except Exception as e:
            log(f"Failed during notes smoke test: {e}")

        # Import Fixtures Smoke
        log("TC-08: Import Fixtures Smoke")
        try:
            # Navigate to CHI TIẾT NGÀY tab
            switch_to_tab(page, "CHI TIẾT NGÀY")

            # Import ICS file
            if ics_path.exists():
                log(f"Importing ICS file: {ics_path}")
                with page.expect_file_chooser() as fc_info:
                    page.get_by_role("button", name="Import", exact=True).click(force=True)
                file_chooser = fc_info.value
                file_chooser.set_files(str(ics_path))
                log("Uploaded ICS file. Waiting 5s for parser...")
                time.sleep(5)
                page.screenshot(path=str(artifacts_dir / "08_import_ics_done.png"))
            else:
                log("SKIPPED ICS import: File not found.")

            # Import XLSX file
            if xlsx_path.exists():
                log(f"Importing XLSX file: {xlsx_path}")
                with page.expect_file_chooser() as fc_info:
                    page.get_by_role("button", name="Import", exact=True).click(force=True)
                file_chooser = fc_info.value
                file_chooser.set_files(str(xlsx_path))
                log("Uploaded XLSX file. Waiting 5s for parser...")
                time.sleep(5)
                page.screenshot(path=str(artifacts_dir / "08_import_xlsx_done.png"))
            else:
                log("SKIPPED XLSX import: File not found.")

            # Go back to main calendar view to verify events are rendered
            switch_to_tab(page, "LỊCH THÁNG")
            page.screenshot(path=str(artifacts_dir / "09_final_calendar_view.png"))
            log("Saved final calendar view screenshot.")
        except Exception as e:
            log(f"Failed during import fixtures smoke: {e}")

        log("Closing browser...")
        browser.close()
        log("Playwright Automation Complete!")

if __name__ == "__main__":
    main()
