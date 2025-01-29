import click
from alembic.config import Config
from alembic import command
import os
import secrets
from pathlib import Path

@click.group()
def cli():
    """CLI tools for managing the application."""
    pass

@cli.command()
def init_db():
    """Initialize the database schema."""
    # Create migrations directory if it doesn't exist
    migrations_dir = Path(__file__).parent.parent / "migrations"
    versions_dir = migrations_dir / "versions"
    versions_dir.mkdir(parents=True, exist_ok=True)

    # Run migrations
    alembic_cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")
    click.echo("Database initialized successfully!")

@cli.command()
def generate_secret():
    """Generate a secure secret key for the application."""
    secret = secrets.token_hex(32)
    click.echo(f"\nGenerated secret key: {secret}")
    click.echo("\nAdd this to your .env file as:")
    click.echo(f"SECRET_KEY={secret}")

if __name__ == '__main__':
    cli()
