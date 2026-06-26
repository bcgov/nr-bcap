from bcap.util.bcap_aliases import AbstractAliases


class BcapMessageAliases(AbstractAliases):
    MESSAGE_AUTHOR = "message_author"
    MESSAGE_CONTENT = "message_content"
    MESSAGE_CREATION_DATE = "message_creation_date"
    MESSAGE_RESPONSE = "message_response"
    MESSAGE_SUBJECT = "message_subject"
    MESSAGE_TYPE = "message_type"
    RECIPIENT = "recipient"
    RELATED_SOURCE_MESSAGE = "related_source_message"
    RESPONSE_AUTHOR = "response_author"
    RESPONSE_COMPLETED = "response_completed"
    RESPONSE_ISSUED_DATE = "response_issued_date"

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(BcapMessageAliases)


class BcapMessageGroupAliases(AbstractAliases):

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(BcapMessageGroupAliases)
