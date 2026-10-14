"""Manual fetching only: disable the legacy unattended refresh timer."""
def enable_manual_mode(g):
    def no_automatic_refresh(self):
        return
    g['App']._top20_auto_tick=no_automatic_refresh
