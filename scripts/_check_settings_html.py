from html.parser import HTMLParser
from pathlib import Path


class P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.pane_stack_when_opened = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.stack.append((tag, attrs.get("id"), attrs.get("class", "")))
        pid = attrs.get("id") or ""
        if pid.startswith("settings-tab-") and "settings-tab-pane" in (attrs.get("class") or ""):
            self.pane_stack_when_opened[pid] = [x[1] for x in self.stack[:-1] if x[1]]

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                return


html = Path("templates/index.html").read_text(encoding="utf-8")
s = html.find('id="page-settings"')
e = html.find('id="page-audit"')
frag = html[s : e if e > s else s + 100000]
parser = P()
parser.feed(frag)
for k, v in parser.pane_stack_when_opened.items():
    print(k, "inside", v)
    bad = [x for x in v if x and x.startswith("settings-tab-")]
    if bad:
        print("BAD NESTING", k, "inside", bad)
