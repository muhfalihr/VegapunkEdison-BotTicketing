INVALID_MESSAGE_IN_USER: str = "/open,/close,/regist,/deregist,/handlers"
BAD_WORDS: str = "jancok,bangsat,bajingan,anjeng,kontol,ngentot,goblok"

MESSAGE_PATTERN: str = "🎫 \*?Ticket\*? #([a-z0-9]+)\n\n🪪 \*?(.*?)\*? \(@([^)]+)\)\n⏰ `?([^`]+)`?\n\n📝 \*?Details :\*?\n([\s\S]+)"
MESSAGE_PATTERN_DETAILS: str = r"📝\s*Details\s*:\s*(.*)"

COMMANDS: str = "/help,/start,/open,/close,/regist,/deregist,/handlers"
TIME_RANGES: str = "today,monthly,weekly,yearly"