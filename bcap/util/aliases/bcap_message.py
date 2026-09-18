from bcap.util.bcap_aliases import AbstractAliases


class BcapMessageAliases(AbstractAliases):
    ARCHIVED_BY = "archived_by"
    ATTACHMENTS = "attachments"
    AUTHOR_RESOLVED_BY = "author_resolved_by"
    AUTHOR_RESOLVED_DATE = "author_resolved_date"
    IS_INTERNAL = "is_internal"
    MESSAGE_AUTHOR = "message_author"
    MESSAGE_CONTENT = "message_content"
    MESSAGE_CREATION_DATE = "message_creation_date"
    MESSAGE_SUBJECT = "message_subject"
    MESSAGE_TYPE = "message_type"
    RECIPIENT = "recipient"
    RECIPIENT_RESOLVED_BY = "recipient_resolved_by"
    RECIPIENT_RESOLVED_DATE = "recipient_resolved_date"
    RELATED_SOURCE_MESSAGE = "related_source_message"
    RESOURCE_CONTEXT = "resource_context"

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(BcapMessageAliases)


class BcapMessageGroupAliases(AbstractAliases):

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(BcapMessageGroupAliases)
