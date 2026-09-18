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
    RELATED_SOURCE_MESSAGE = "related_source_message"
    RESOURCE_CONTEXT = "resource_context"
    THREAD_RESOLVED_BY = "thread_resolved_by"
    THREAD_RESOLVED_DATE = "thread_resolved_date"

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(BcapMessageAliases)


class BcapMessageGroupAliases(AbstractAliases):

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(BcapMessageGroupAliases)
