from django.db import transaction


def delete_file_on_commit(file_field):
    """
    Schedules the deletion of an uploaded file from storage backend (local or cloud)
    after the active database transaction successfully commits to prevent orphans.
    """
    if not file_field or not file_field.name:
        return

    file_name = file_field.name
    storage = file_field.storage

    def _delete():
        try:
            if storage.exists(file_name):
                storage.delete(file_name)
        except Exception:
            pass

    transaction.on_commit(_delete)
