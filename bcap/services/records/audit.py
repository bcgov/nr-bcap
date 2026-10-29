"""Per-user log of file reads. The store only sees BCAP's own key, so this is
the only record of who read what. Restricted reads are picked out at review
time by joining the fileid to the object's sensitivity-class tag.
"""

import logging

audit = logging.getLogger("bcap.records.file_access")


class RecordsAuditService:
    @staticmethod
    def log_read(fileid, user, status, thumbnail):
        audit.info(
            "read fileid=%s user=%s userid=%s thumbnail=%s status=%s",
            fileid,
            user.username or "anonymous",
            user.pk,
            thumbnail,
            status,
        )
