#!/usr/bin/env python3
"""
GitHub Trending 可靠数据获取脚本
为 github-trending skill 提供干净结构化 JSON，避免 LLM 直接解析易变的 HTML。

用法示例:
  python3 fetch_trending.py --since daily --limit 8
  python3 fetch_trending.py --since weekly --language Rust --limit 5
  python3 fetch_trending.py --developers --since daily --limit 10
  python3 fetch_trending.py --since monthly --spoken-language "Chinese" --limit 10

输出: stdout JSON
  {
    "meta": {"source": "github-trending-scrape", "since": "daily", "language": "...", "count": N, "fetched_at": "..."},
    "items": [ { "rank": 1, "full_name": "owner/repo", "url": "...", "description": "...", "language": "...", "stars": 12345, "stars_today": 234, "forks": 123, "owner": "...", "name": "..." }, ... ]
  }

首次使用:
  pip install requests beautifulsoup4 lxml

错误处理: 所有失败均输出带 error 的 JSON + 非零退出，绝不静默。
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

try:
    import requests
    from bs4 import BeautifulSoup, Tag
except ImportError as e:
    err = {
        "error": "缺少依赖",
        "missing": str(e),
        "suggestion": "pip install requests beautifulsoup4 lxml",
        "command_example": "pip install requests beautifulsoup4 lxml"
    }
    print(json.dumps(err, ensure_ascii=False))
    sys.exit(1)

GITHUB_BASE = "https://github.com"
TRENDING_URL = f"{GITHUB_BASE}/trending"
DEVELOPERS_URL = f"{GITHUB_BASE}/trending/developers"
DEFAULT_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


def build_url(since: str = "daily", language: Optional[str] = None, spoken_language: Optional[str] = None, developers: bool = False) -> str:
    base = DEVELOPERS_URL if developers else TRENDING_URL
    params: Dict[str, str] = {"since": since}
    if language:
        # GitHub uses slug like "rust", "python", "c++" → "c%2B%2B"
        lang_slug = language.lower().replace(" ", "-").replace("++", "%2B%2B").replace("#", "%23")
        base = f"{base}/{lang_slug}"
    if spoken_language:
        params["spoken_language_code"] = spoken_language  # e.g. "zh", "en", or full? GitHub accepts code like "Chinese"
    return f"{base}?{urlencode(params)}" if params else base


def fetch_html(url: str) -> str:
    headers = {
        "User-Agent": DEFAULT_UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        raise RuntimeError(f"请求失败: {e} (URL: {url})") from e


def safe_text(tag: Optional[Tag], strip: bool = True) -> str:
    if not tag:
        return ""
    text = tag.get_text()
    return text.strip() if strip else text


def parse_stars(text: str) -> int:
    if not text:
        return 0
    t = text.lower().replace(",", "").replace(" ", "").strip()
    if "k" in t:
        try:
            return int(float(t.replace("k", "")) * 1000)
        except ValueError:
            return 0
    try:
        return int("".join(c for c in t if c.isdigit()))
    except ValueError:
        return 0


def parse_repository(article: Tag) -> Optional[Dict[str, Any]]:
    """解析单个仓库条目，容错优先"""
    try:
        # 仓库链接和名称 (h2.h3 > a)
        h2 = article.select_one("h2.h3, h2.lh-condensed, h2")
        link = h2.select_one("a") if h2 else article.select_one("a[href*='/'][itemprop]")
        if not link:
            link = article.select_one("a[href^='/'][class*='Link']")
        if not link:
            return None

        href = link.get("href", "").strip()
        if not href or not href.startswith("/"):
            return None
        full_name = href.strip("/")

        # 描述
        desc_tag = article.select_one("p.my-1, p.col-9, p.color-fg-muted, p")
        description = safe_text(desc_tag)

        # 语言
        language = ""
        for selector in ("span[itemprop='programmingLanguage']", "span.language"):
            language = safe_text(article.select_one(selector))
            if language:
                break
        if not language:
            for span in article.select(".f6 .d-inline-block span"):
                candidate = safe_text(span)
                if candidate:
                    language = candidate
                    break

        # Stars 总数
        stars_tag = article.select_one("a[href$='/stargazers'], a[href*='stargazers']")
        stars_text = safe_text(stars_tag)
        stars = parse_stars(stars_text)

        # 今日新增 (常见于 "X stars today" 或小 span)
        today_tag = article.select_one("span.d-inline-block.float-sm-right, span:-soup-contains('stars today'), small")
        stars_today_text = safe_text(today_tag)
        stars_today = parse_stars(stars_today_text)
        # 兜底：有些页面在 title 或相邻文本
        if stars_today == 0 and "stars today" in article.get_text().lower():
            m = re.search(r"(\d[\d,]*)\s*stars? today", article.get_text(), re.I)
            if m:
                stars_today = parse_stars(m.group(1))

        # Forks (可选)
        forks_tag = article.select_one("a[href$='/forks'], a[href*='forks']")
        forks = parse_stars(safe_text(forks_tag))

        owner, name = full_name.split("/", 1) if "/" in full_name else (full_name, "")

        return {
            "rank": 0,  # 由调用方填充
            "full_name": full_name,
            "owner": owner,
            "name": name,
            "url": f"{GITHUB_BASE}/{full_name}",
            "description": description[:300] if description else "",
            "language": language,
            "stars": stars,
            "stars_today": stars_today,
            "forks": forks,
        }
    except Exception:
        return None


def parse_developer(article: Tag) -> Optional[Dict[str, Any]]:
    """解析开发者趋势条目"""
    try:
        # 开发者链接通常在 h1/h2 + a
        link = article.select_one("h1 a, h2 a, a[data-hovercard-type='user']")
        if not link:
            link = article.select_one("a[href^='/'][class*='Link']")
        if not link:
            return None

        href = link.get("href", "").strip("/")
        if not href or "/" in href:  # 跳过组织等
            # 有些是 /org/repo 形式，跳过
            return None

        # 名称
        name = safe_text(link)
        # 登录
        login_tag = article.select_one("span.text-normal, p.f4, .f6 a")
        login = safe_text(login_tag) or href.split("/")[-1]

        # 仓库贡献描述
        repo_tag = article.select_one("a[href*='/'][class*='repo'] , .h4 a, .f6 a")
        popular_repo = safe_text(repo_tag)

        # 粉丝/贡献
        followers_tag = article.select_one("span:-soup-contains('followers'), a[href*='followers']")
        followers = parse_stars(safe_text(followers_tag))

        return {
            "rank": 0,
            "login": login,
            "name": name,
            "url": f"{GITHUB_BASE}/{href}",
            "popular_repository": popular_repo[:120] if popular_repo else "",
            "followers": followers,
            "type": "developer",
        }
    except Exception:
        return None


def scrape_trending(url: str, developers: bool = False, limit: int = 10) -> List[Dict[str, Any]]:
    html = fetch_html(url)
    soup = BeautifulSoup(html, "lxml")

    # 主要容器：article.Box-row (2025-2026 仍有效)
    articles = soup.select("article.Box-row")
    if not articles:
        # 兜底：某些布局变化
        articles = soup.select("div.Box-row, article")

    items: List[Dict[str, Any]] = []
    parser = parse_developer if developers else parse_repository

    for idx, article in enumerate(articles[: max(limit, 25)]):
        item = parser(article)
        if item:
            item["rank"] = idx + 1
            items.append(item)

    # 轻微延迟，礼貌
    time.sleep(0.2)
    return items[:limit]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="GitHub Trending 结构化数据抓取 (为 AI skill 设计)"
    )
    parser.add_argument("--since", choices=["daily", "weekly", "monthly"], default="daily",
                        help="时间范围 (默认 daily)")
    parser.add_argument("--language", "-l", default=None,
                        help="编程语言过滤，如 Rust, Python, TypeScript, 'C++'")
    parser.add_argument("--spoken-language", default=None,
                        help="自然语言过滤，如 Chinese, English, Japanese (GitHub spoken_language_code)")
    parser.add_argument("--developers", "-d", action="store_true",
                        help="抓取开发者榜 (默认仓库榜)")
    parser.add_argument("--limit", "-n", type=int, default=10,
                        help="返回条数上限 (1-25，默认 10)")
    parser.add_argument("--format", choices=["json"], default="json",
                        help="输出格式 (仅 json)")

    args = parser.parse_args()

    if args.limit < 1 or args.limit > 25:
        print(json.dumps({"error": "limit 必须在 1-25 之间"}, ensure_ascii=False))
        sys.exit(1)

    url = build_url(
        since=args.since,
        language=args.language,
        spoken_language=args.spoken_language,
        developers=args.developers
    )

    try:
        items = scrape_trending(url, developers=args.developers, limit=args.limit)
        result = {
            "meta": {
                "source": "github-trending-scrape",
                "url": url,
                "since": args.since,
                "language": args.language or "",
                "spoken_language": args.spoken_language or "",
                "mode": "developers" if args.developers else "repositories",
                "count": len(items),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "note": "数据来自 HTML 解析，GitHub 页面结构可能变化。建议结合 API 二次校验。"
            },
            "items": items
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        err = {
            "error": str(e),
            "url": url,
            "suggestion": "检查网络、GitHub 是否限流，或稍后重试。必要时自托管 https://github.com/NiklasTiede/Github-Trending-API"
        }
        print(json.dumps(err, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
