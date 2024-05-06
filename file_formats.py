formats = []


def get_formats_str():
    return [format.name for format in formats]


def get_format(format_str: str):
    for format in formats:
        if format.name.lower() == format_str.lower():
            return format


class FileType:
    Video = 0
    Audio = 1


class FileFormat:
    def __init__(self, name: str, file_type):
        self.name = name.lower()
        self.file_type = file_type
        formats.append(self)


MP4 = FileFormat("MP4", FileType.Video)
MOV = FileFormat("MOV", FileType.Video)
AVI = FileFormat("AVI", FileType.Video)
WMV = FileFormat("WMV", FileType.Video)
FLV = FileFormat("FLV", FileType.Video)
WEBM = FileFormat("WEBM", FileType.Video)
MP3 = FileFormat("MP3", FileType.Audio)
WAV = FileFormat("WAV", FileType.Audio)
M4A = FileFormat("M4A", FileType.Audio)
FLAC = FileFormat("FLAC", FileType.Audio)
