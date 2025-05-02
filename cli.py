import click
from db import init_db, get_cached, cache_tags
from scraper import scrape_tiktok
from generator import draft_script, generate_video
import openai, sys, os
import asyncio
if sys.platform.startswith("win"):
    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)

@click.group()
def cli():
    """Trend-Aware Brand Video CLI"""
    init_db()

@cli.command()
@click.option("--platform", default="TikTok", help="Platform to scrape")
@click.option("--limit", default=10, help="Number of tags")
def fetch_trends(platform, limit):
    """Fetch and cache trending tags."""
    tags = get_cached(platform)
    if not tags:
        click.echo(f"No recent cache for {platform}, scraping…")
        tags = scrape_tiktok(limit)
        cache_tags(platform, tags)
    else:
        click.echo(f"Using cached tags from last hour.")
    click.echo("\n".join(f"{i+1}. {t}" for i, t in enumerate(tags)))

@cli.command()
@click.option("--trend", prompt="Trend hashtag", help="Trend to use")
@click.option("--brand", prompt="Brand name", help="Brand or product")
@click.option("--tone", default="Funny", help="Video tone")
@click.option("--audio", default=None, help="Path to audio file (optional)")
@click.option("--output", default="out.mp4", help="Output video path")
def generate(trend, brand, tone, audio, output):
    """Draft script and render a video."""
    # set API key
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        click.echo("ERROR: Set OPENAI_API_KEY env var.", err=True)
        sys.exit(1)
    openai.api_key = key

    click.echo("Drafting script…")
    script = draft_script(brand, trend, tone)
    click.echo("Script JSON:")
    click.echo(script)

    if not audio:
        click.echo("WARNING: No audio file provided; final video will be silent.")
    click.echo("Rendering video (this may take a while)…")
    video_path = generate_video(script, audio or "", output)
    click.echo(f"Video saved to {video_path}")

if __name__ == "__main__":
    cli()
