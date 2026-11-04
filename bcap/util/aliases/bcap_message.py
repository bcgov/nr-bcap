from bcap.util.bcap_aliases import AbstractAliases


class BcapMessageAliases(AbstractAliases):
    ARCHIVED_BY = "archived_by"
    ATTACHMENTS = "attachments"
    IS_INTERNAL = "is_internal"
    MESSAGE_AUTHOR = "message_author"
    MESSAGE_CONTENT = "message_content"
    MESSAGE_CREATION_DATE = "message_creation_date"
    MESSAGE_SUBJECT = "message_subject"
    MESSAGE_TYPE = "message_type"
    RECIPIENT = "recipient"
    RESOURCE_CONTEXT = "resource_context"
    THREAD = "thread"
    THREAD_ANSWERED = "thread_answered"
    THREAD_AUTHOR_RESOLVED_BY = "thread_author_resolved_by"
    THREAD_AUTHOR_RESOLVED_DATE = "thread_author_resolved_date"
    THREAD_LAST_MESSAGE_DATE = "thread_last_message_date"
    THREAD_PARTICIPANTS = "thread_participants"
    THREAD_RECIPIENT_RESOLVED_BY = "thread_recipient_resolved_by"
    THREAD_RECIPIENT_RESOLVED_DATE = "thread_recipient_resolved_date"

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(BcapMessageAliases)


class BcapMessageGroupAliases(AbstractAliases):

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(BcapMessageGroupAliases)
