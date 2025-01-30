import click
from alembic.config import Config
from alembic import command
import os
import secrets
from pathlib import Path
from sqlalchemy import create_engine, text

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
        # Get database path from alembic.ini
        alembic_cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))
        db_url = alembic_cfg.get_main_option("sqlalchemy.url")
        
        # Create engine
        engine = create_engine(db_url)
        
        # Drop all tables
        with engine.connect() as conn:
            # Get all table names
            tables = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"))
            table_names = [table[0] for table in tables]
            
            # Drop each table
            for table in table_names:
                conn.execute(text(f"DROP TABLE IF EXISTS {table};"))
            conn.commit()
            
            click.echo(f"Dropped tables: {', '.join(table_names)}")
        
        # Run migrations to create fresh tables
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
