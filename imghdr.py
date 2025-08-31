# Мини-реализация imghdr для Python 3.13+ (модуль удалён из stdlib).
# Достаточно для нужд python-telegram-bot 13.x (png/jpeg/gif/bmp).

def what(file, h=None):
    def _readhead(f):
        if hasattr(f, "read"):
            pos = f.tell()
            head = f.read(32)
            f.seek(pos)
            return head
        with open(f, "rb") as fh:
            return fh.read(32)

    if h is None:
        try:
            h = _readhead(file)
        except Exception:
            return None
    if not h:
        return None

    if h.startswith(b"\xff\xd8"):
        return "jpeg"
    if h.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if h[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if h.startswith(b"BM"):
        return "bmp"
    return None
