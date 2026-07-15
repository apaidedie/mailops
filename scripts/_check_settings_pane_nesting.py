from html.parser import HTMLParser
from pathlib import Path


class Checker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.pane_parents = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.stack.append((tag, attrs.get("id"), attrs.get("class", "")))
        pid = attrs.get("id") or ""
        if pid.startswith("settings-tab-") and "pane" in attrs.get("class", ""):
            # parent chain of ids
            parents = [x[1] for x in self.stack[:-1] if x[1]]
            self.pane_parents[pid] = parents

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                self.stack = self.stack[:i]
                break


html = Path("templates/index.html").read_text(encoding="utf-8")
# only page-settings fragment
start = html.find('id="page-settings"')
end = html.find('id="page-audit"')
if end < 0:
    end = html.find('<!-- ===== Page: Audit')
chunk = html[start:end] if end > start else html[start:]
# wrap for parser
c = Checker()
c.feed("<div>" + chunk + "</div>")
for pane, parents in c.pane_parents.items():
    print(pane, "parents=", parents)
    nested_in_other = [p for p in parents if p.startswith("settings-tab-")]
    if nested_in_other:
        print("  *** NESTED IN OTHER PANE ***", nested_in_other)
