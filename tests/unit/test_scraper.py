from __future__ import annotations

import pytest

try:
    import httpx
    import respx
except ImportError:
    pytest.skip("respx not installed", allow_module_level=True)

from src.config import ScraperConfig
from src.scraper import Scraper, ScraperError

SAMPLE_HTML = """
<!DOCTYPE html>
<html>
  <head><title>Test Page</title></head>
  <body><h1>Hello, world!</h1><p>Some content.</p></body>
</html>
"""


@pytest.fixture
def cfg() -> ScraperConfig:
    return ScraperConfig(base_url="https://test.example.com", request_timeout=5, rate_limit_delay=0)


@pytest.mark.asyncio
async def test_fetch_html_parses_title(respx_mock: respx.MockRouter, cfg: ScraperConfig) -> None:
    respx_mock.get("https://test.example.com/page").mock(return_value=httpx.Response(200, text=SAMPLE_HTML))
    async with Scraper(cfg) as scraper:
        soup = await scraper.fetch_html("/page")
    assert soup.title is not None
    assert soup.title.string == "Test Page"


@pytest.mark.asyncio
async def test_fetch_html_parses_heading(respx_mock: respx.MockRouter, cfg: ScraperConfig) -> None:
    respx_mock.get("https://test.example.com/page").mock(return_value=httpx.Response(200, text=SAMPLE_HTML))
    async with Scraper(cfg) as scraper:
        soup = await scraper.fetch_html("/page")
    h1 = soup.find("h1")
    assert h1 is not None
    assert h1.get_text(strip=True) == "Hello, world!"


@pytest.mark.asyncio
async def test_fetch_html_raises_on_404(respx_mock: respx.MockRouter, cfg: ScraperConfig) -> None:
    respx_mock.get("https://test.example.com/missing").mock(return_value=httpx.Response(404))
    with pytest.raises(ScraperError, match="HTTP 404"):
        async with Scraper(cfg) as scraper:
            await scraper.fetch_html("/missing")


@pytest.mark.asyncio
async def test_fetch_html_raises_on_500(respx_mock: respx.MockRouter, cfg: ScraperConfig) -> None:
    respx_mock.get("https://test.example.com/broken").mock(return_value=httpx.Response(500))
    with pytest.raises(ScraperError, match="HTTP 500"):
        async with Scraper(cfg) as scraper:
            await scraper.fetch_html("/broken")


@pytest.mark.asyncio
async def test_scraper_requires_context_manager(cfg: ScraperConfig) -> None:
    scraper = Scraper(cfg)
    with pytest.raises(RuntimeError):
        await scraper.fetch_html("/any")
