"""Text emoticons shared by outline and Markdown labels."""
import re


_GROUPS = {
    "🙂": (":-)", ":)"),
    "😐": (":-|", ":|"),
    "🙁": (":-(", ":("),
    "😉": (";-)", ";)"),
    "😃": (":-D", ":D", ":-d", ":d"),
    "😆": ("XD", "xD", "X-D", "x-D"),
    "😛": (":-P", ":P", ":-p", ":p"),
    "😜": (";-P", ";P", ";-p", ";p"),
    "😮": (":-O", ":O", ":-o", ":o"),
    "😕": (":-/", ":/", ":-\\", ":\\"),
    "😢": (":'-(", ":'("),
    "😂": (":'-)", ":')"),
    "😎": ("8-)", "8)", "B-)", "B)"),
    "😗": (":-*", ":*"),
    "😇": ("O:-)", "O:)", "0:-)", "0:)"),
    "😈": (">:-)", ">:)"),
    "😠": (">:-(", ">:("),
    "🤐": (":-X", ":X", ":-x", ":x"),
    "😳": (":-$", ":$"),
    "❤️": ("<3",),
    "💔": ("</3",),
}
_EMOTICONS = {text: emoji for emoji, forms in _GROUPS.items() for text in forms}
_PATTERN = re.compile(r"(?<![\w:/\\])(?:" + '|'.join(
    re.escape(text) for text in sorted(_EMOTICONS, key=len, reverse=True)
) + r")(?![\w/\\])")


def MatchEmoticon(text, position):
    return _PATTERN.match(text, position)


def ReplaceEmoticons(text):
    return _PATTERN.sub(lambda match: _EMOTICONS[match.group(0)], text)
