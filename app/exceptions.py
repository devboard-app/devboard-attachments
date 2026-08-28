

class AttachmentNotFoundException(Exception):
    pass
class TooManyAttachmentsException(Exception):
    pass
class InvalidTypeFileException(Exception):
    pass

class FileTooLargeException(Exception):
    pass

class FileNotUploadedException(Exception):
    pass

class FileSizeMissmatchException(Exception):
    pass


class NotAttachmentOwnerException(Exception):
    pass

class AttachmentNotStoredException(Exception):
    pass