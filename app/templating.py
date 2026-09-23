from pathlib import Path

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


def _fmt(n, dash_zero=False):
    if n is None:
        return ""
    n = round(n)
    if n == 0:
        return "-" if dash_zero else "0"
    s = f"{abs(n):,.0f}".replace(",", " ")
    return f"({s})" if n < 0 else s


def _fmt_date(d):
    if d is None:
        return ""
    return d.strftime("%d %B %Y").lstrip("0")


templates.env.filters["rand"] = _fmt
templates.env.filters["afsdate"] = _fmt_date
