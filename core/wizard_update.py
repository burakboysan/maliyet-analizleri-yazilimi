def refresh_summary_container(summary_container, render_summary):
    if summary_container is None:
        return False
    try:
        if not summary_container.winfo_exists():
            return False
    except Exception:
        return False

    for child in summary_container.winfo_children():
        child.destroy()
    render_summary(summary_container)
    return True


def update_after_selection(field_name, summary_only_fields, refresh_summary, render_step):
    if field_name in summary_only_fields and refresh_summary():
        return
    render_step()
