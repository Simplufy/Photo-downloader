"""Command-line interface for the photo downloader."""

import logging
import sys

import click

from .config import Config
from .orchestrator import Orchestrator


@click.group()
@click.option("--config", "-c", default=None, help="Path to config file")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.pass_context
def cli(ctx, config, verbose, debug):
    """Photo Downloader - Download and categorize luxury car images."""
    # Setup logging
    level = logging.DEBUG if debug else (logging.INFO if verbose else logging.WARNING)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    ctx.ensure_object(dict)
    ctx.obj["config"] = Config(config)


@cli.command()
@click.option("--brand", "-b", default=None, help="Download only this brand")
@click.option("--model", "-m", default=None, help="Download only this model (requires --brand)")
@click.option("--year", "-y", default=None, type=int, help="Download only this year")
@click.option("--limit", "-l", default=None, type=int, help="Override images per combination")
@click.option("--source", "-s", default=None, help="Use only this source (e.g. netcarshow, wikimedia)")
@click.option("--dry-run", is_flag=True, help="Show what would be downloaded without downloading")
@click.pass_context
def download(ctx, brand, model, year, limit, source, dry_run):
    """Download images for configured brands/models/years."""
    config = ctx.obj["config"]

    if model and not brand:
        click.echo("Error: --model requires --brand to be specified")
        sys.exit(1)

    if limit:
        config._data["images_per_combination"] = limit

    orchestrator = Orchestrator(config)

    # Filter brands - now returns {brand: {model: [years]}}
    brands = config.get_brand_models(brand)
    if brand and not brands:
        click.echo(f"Error: Brand '{brand}' not found in config")
        sys.exit(1)

    # Filter models
    if model:
        brand_models = brands.get(brand, {})
        if model not in brand_models:
            click.echo(f"Error: Model '{model}' not found for brand '{brand}'")
            sys.exit(1)
        brands = {brand: {model: brand_models[model]}}

    # Filter years - apply to each model's year list
    if year:
        filtered = {}
        for b, models in brands.items():
            filtered_models = {}
            for m, years_list in models.items():
                if year in years_list:
                    filtered_models[m] = [year]
            if filtered_models:
                filtered[b] = filtered_models
        brands = filtered

    # Filter sources
    source_filter = source

    total_combos = sum(
        len(yrs) for models in brands.values() for yrs in models.values()
    )

    cat_targets = config.category_targets
    breakdown = " + ".join(f"{n} {c}" for c, n in cat_targets.items())

    click.echo("=" * 60)
    click.echo("Photo Downloader")
    click.echo("=" * 60)
    click.echo(f"Brands:  {len(brands)}")
    click.echo(f"Combos:  {total_combos}")
    click.echo(f"Target:  {config.images_per_combination} per combo ({breakdown})")
    click.echo(f"Output:  {config.download_dir}")
    if dry_run:
        click.echo("Mode:    DRY RUN (no downloads)")
    click.echo("=" * 60)

    orchestrator.run(
        brands=brands,
        source_filter=source_filter,
        dry_run=dry_run,
    )


@cli.command()
@click.pass_context
def status(ctx):
    """Show download status and statistics."""
    config = ctx.obj["config"]
    orchestrator = Orchestrator(config)
    orchestrator.show_status()


@cli.command("list-brands")
@click.pass_context
def list_brands(ctx):
    """List all configured brands and models."""
    config = ctx.obj["config"]
    brands = config.get_brand_models()

    click.echo("Configured brands and models:")
    click.echo("-" * 40)
    for brand, models in sorted(brands.items()):
        click.echo(f"\n{brand}:")
        for model, years in sorted(models.items()):
            click.echo(f"  - {model} ({years[0]}-{years[-1]})")


@cli.command("list-sources")
@click.pass_context
def list_sources(ctx):
    """List all configured sources."""
    config = ctx.obj["config"]
    sources = config.get_enabled_sources()

    click.echo("Configured sources (in priority order):")
    click.echo("-" * 40)
    for src in sources:
        status = "enabled" if src.get("enabled", True) else "disabled"
        click.echo(f"  [{status}] {src['name']}: {src['base_url']}")


def main():
    cli(obj={})


if __name__ == "__main__":
    main()
