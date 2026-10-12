# ChotuApp R3 touchpad update

Shopify public-catalog extractor with a desktop GUI and ChotuApp workbook export.
R3 adds tap-hold/left-button drag scrolling on store rows and page backgrounds.
A normal store click still toggles selection; dragging a row does not. Text fields,
buttons and scrollbar controls retain their normal actions. Two-finger gestures
that send MouseWheel events retain wheel support. Real hardware validation is pending.

R2 handles wheel events sent to a focused root while hovering over a scroll pane,
pins FETCH SELECTED above the page, and persists the selected template.
The original RAR and historical files are preserved. `main.py` is the extracted,
updated source; the archive itself is not updated.

## Windows update

Close ChotuApp first. Extract `ChotuApp_Fixed.zip` into a separate folder.
Open a terminal in that folder and run:

```bat
py install_update.py
py "%USERPROFILE%\Desktop\ChotuApp_Software\main.py"
```

For a different installation location:

```bat
py install_update.py --target "D:\your\ChotuApp_Software"
```

The installer verifies a timestamped backup before replacing only `main.py`.
It preserves Excel exports, checkpoints, configuration and historical backups.
If your current Python environment lacks dependencies, run:

```bat
py -m pip install -r requirements.txt
```

Choose the original seller template using Browse file. Add stores, tick stores,
then use **Start selected**. **Refresh all** processes the full list.
Pause takes effect at the next safe point; an active HTTP request can finish first.
A website's rate limit still causes a wait; throttling is respected.
REVIEW REQUIRED means a workbook was saved but its audit needs attention.
Prices retain the existing integer truncation policy and original API audits.

## Verified changes

- Mouse-wheel routing runs before nested widget/global handlers, with independent
  store, page and text-pane scrolling. New rows receive bindings after redraw.
- Selected-store indexing follows URLs; the selected start button reflects selection.
- Worker exceptions restore controls; idle Pause has no effect; retry waits honor Pause.
- REVIEW results have their own status instead of appearing as an approved completion.
- Folder opening works through the appropriate Windows/macOS/Linux command.
- `CHOTUAPP_DATA_DIR` optionally sets the Desktop data/config location.

## Development and tests

Python 3.12, Tk and pinned runtime dependencies were used in cloud validation.
With a working graphical DISPLAY (or virtual X display):

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python main.py
```

The tests exercise pane scrolling, simulated Windows wheel events, selection,
Pause/Resume, worker failures, REVIEW status, HTTP-to-XLSX export, variant
availability, decimal truncation, and preservation of an existing FINAL workbook.
The schema fixture contains headers from an archived workbook, without customer
records. Export tests use a local HTTP server and temporary directories.

Actual Windows mouse/trackpad behavior and live-store export still need validation.
The original seller template was not supplied. No live catalog, real Excel exports,
or remote websites were altered during the tests.
