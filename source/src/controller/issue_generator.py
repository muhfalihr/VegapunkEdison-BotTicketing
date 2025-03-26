from telebot.types import Message


class IssueGenerator:
    def __init__(self):
        pass

    async def issue_generator(self, message: Message):
        issue = "..."
        message_content_type = message.content_type
        
        if message_content_type == "text":
            issue = message.text
        elif message_content_type == "document":
            issue = (
                f"Document File ID: {message.document.file_id}"
                f"Documenet File Unique ID: {message.document.file_unique_id} "
                f"Document File Name: {message.document.file_name} "
                f"Document Mime Type: {message.document.mime_type} "
                f"Document File Size: {message.document.file_size} "
                f"Document Caption: {message.caption or issue}"
            )
        elif message_content_type == "photo":
            issue = (
                f"Photo File ID: {message.photo[-1].file_id}"
                f"Photo File Unique ID: {message.photo[-1].file_unique_id} "
                f"Photo File Size: {message.photo[-1].file_size} "
                f"Photo Height: {message.photo[-1].height} "
                f"Photo Width: {message.photo[-1].width} "
                f"Photo Caption: {message.caption or issue} "
            )
        elif message_content_type == "video":
            issue = (
                f"Video File ID: {message.video.file_id}"
                f"Video File Unique ID: {message.video.file_unique_id} "
                f"Video File Size: {message.video.file_size} "
                f"Video Height: {message.video.height} "
                f"Video Width: {message.video.width} "
                f"Video Duration: {message.video.duration} "
                f"Video Caption: {message.caption or issue} "
            )
        return issue