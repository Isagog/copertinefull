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
    try:
        # Create migrations directory if it doesn't exist
        migrations_dir = Path(__file__).parent.parent / "migrations"
        versions_dir = migrations_dir / "versions"
        versions_dir.mkdir(parents=True, exist_ok=True)

        # Run migrations
        alembic_cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))
        
        # Check current revision
        with alembic_cfg.get_engine().connect() as connection:
            context = command.get_context(alembic_cfg, connection)
            current_rev = context.get_current_revision()
            
            if current_rev:
                click.echo("Database is already initialized.")
                click.echo("To reset the database, use: copertine-cli reset-db")
                return
        
        command.upgrade(alembic_cfg, "head")
        click.echo("Database initialized successfully!")
    except Exception as e:
        click.echo(f"Error initializing database: {str(e)}", err=True)
        raise click.Abort()

@cli.command()
def reset_db():
    """Reset the database schema (WARNING: This will delete all data)."""
    if not click.confirm('This will delete all data. Are you sure?'):
        click.echo('Operation cancelled.')
        return
    
    try:
        alembic_cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))
        
        # Drop all tables
        command.downgrade(alembic_cfg, "base")
        
        # Recreate tables
        command.upgrade(alembic_cfg, "head")
        
        click.echo("Database reset successfully!")
    except Exception as e:
        click.echo(f"Error resetting database: {str(e)}", err=True)
        raise click.Abort()

@cli.command()
def generate_secret():
    """Generate a secure secret key for the application."""
    secret = secrets.token_hex(32)
    click.echo(f"\nGenerated secret key: {secret}")
    click.echo("\nAdd this to your .env file as:")
    click.echo(f"SECRET_KEY={secret}")

if __name__ == '__main__':
    cli()
