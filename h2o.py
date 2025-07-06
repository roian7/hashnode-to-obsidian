#!/usr/bin/env python3
"""
Hashnode to Obsidian Converter (h2o)

A Python CLI tool for converting Hashnode blog exports to Obsidian-compatible format.
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from converter import HashNodeParser, HashNodeEnricher, ImageHandler
from obsidian_transformer import ObsidianTransformer
import re

console = Console()

# Load environment variables
load_dotenv()




@click.command()
@click.argument('export_file', type=click.Path(exists=True, path_type=Path))
@click.option('--output', '-o', type=click.Path(path_type=Path), default=Path('./obsidian-vault'),
              help='Output directory for generated files')
@click.option('--limit', '-l', type=int, help='Limit number of posts to process (for testing)')
@click.option('--skip-enrichment', is_flag=True, 
              help='Skip API enrichment (tags will show as IDs)')
@click.option('--skip-images', is_flag=True,
              help='Skip image downloads (use remote URLs)')
@click.option('--api-key', type=str, help='Hashnode API key (overrides HASHNODE_API_KEY env var)')
@click.option('--dry-run', is_flag=True, help='Show what would be done without writing files')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
def cli(export_file: Path, output: Path, limit: Optional[int], skip_enrichment: bool,
        skip_images: bool, api_key: Optional[str], dry_run: bool, verbose: bool):
    """
    Convert Hashnode blog export to Obsidian-compatible format.
    
    EXPORT_FILE: Path to the Hashnode JSON export file
    """
    
    # Set up console logging
    if verbose:
        console.print(f"[blue]Export file: {export_file}[/blue]")
        console.print(f"[blue]Output directory: {output}[/blue]")
        if limit:
            console.print(f"[blue]Limit: {limit} posts[/blue]")
        console.print(f"[blue]Skip enrichment: {skip_enrichment}[/blue]")
        console.print(f"[blue]Skip images: {skip_images}[/blue]")
        console.print(f"[blue]Dry run: {dry_run}[/blue]")
        console.print()
    
    try:
        converter = HashNodeToObsidianConverter(
            api_key=api_key,
            skip_enrichment=skip_enrichment,
            skip_images=skip_images,
            verbose=verbose
        )
        
        converter.convert(
            export_file=export_file,
            output_dir=output,
            limit=limit,
            dry_run=dry_run
        )
        
    except KeyboardInterrupt:
        console.print("\n[red]Conversion interrupted by user[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Conversion failed: {e}[/red]")
        if verbose:
            console.print_exception()
        sys.exit(1)


class HashNodeToObsidianConverter:
    """Main converter orchestrating the conversion process for Obsidian."""
    
    def __init__(self, api_key: Optional[str] = None, skip_enrichment: bool = False,
                 skip_images: bool = False, verbose: bool = False):
        """Initialize converter with options."""
        self.api_key = api_key or os.getenv('HASHNODE_API_KEY')
        self.skip_enrichment = skip_enrichment
        self.skip_images = skip_images
        self.verbose = verbose
        
        # Initialize components
        self.enricher = HashNodeEnricher(api_key=self.api_key)
        self.transformer = ObsidianTransformer()
        self.image_handler = ImageHandler()
        
    def convert(self, export_file: Path, output_dir: Path, limit: Optional[int] = None,
                dry_run: bool = False) -> None:
        """Main conversion process."""
        
        console.print("🚀 [bold blue]Starting Hashnode to Obsidian conversion...[/bold blue]\n")
        
        # Phase 1: Parse export file
        console.print("📋 [blue]Phase 1: Parsing export file...[/blue]")
        parser = HashNodeParser(str(export_file))
        parser.load_export()
        
        summary = parser.get_summary()
        posts = parser.get_posts(limit=limit)
        
        console.print(f"   Found {summary['total_posts']} posts from publication: {summary['publication_title']}")
        if limit and limit < summary['total_posts']:
            console.print(f"   [yellow]Limited to {limit} posts for testing[/yellow]")
        console.print()
        
        # Phase 2: Enrich data
        if self.skip_enrichment:
            console.print("⏭️  [yellow]Phase 2: Skipping API enrichment (--skip-enrichment flag)...[/yellow]")
            enriched_data = self.enricher.create_fallback_enrichment(posts)
        elif not self.enricher.can_enrich():
            console.print("⏭️  [yellow]Phase 2: Skipping API enrichment (no API key)...[/yellow]")
            enriched_data = self.enricher.create_fallback_enrichment(posts)
        else:
            console.print("🔍 [blue]Phase 2: Enriching data from Hashnode API...[/blue]")
            post_ids = [post['_id'] for post in posts]
            enriched_data = self.enricher.enrich_posts(post_ids)
            
        console.print()
        
        # Phase 3: Transform content to Obsidian format
        console.print("📝 [blue]Phase 3: Transforming content to Obsidian format...[/blue]")
        transformed_posts = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("Transforming posts", total=len(posts))
            
            for post in posts:
                post_id = post['_id']
                enriched_post = enriched_data.get(post_id, {})
                
                if not enriched_post:
                    console.print(f"[yellow]Warning: No enriched data for post {post_id}[/yellow]")
                    continue
                    
                transformed_post = self.transformer.transform_post(post, enriched_post)
                transformed_posts.append(transformed_post)
                
                progress.advance(task)
                
        console.print(f"   Processed {len(transformed_posts)} posts")
        console.print()
        
        # Phase 4: Process images with new folder structure
        if self.skip_images:
            console.print("⏭️  [yellow]Phase 4: Skipping image downloads...[/yellow]")
        else:
            console.print("🖼️  [blue]Phase 4: Processing images...[/blue]")
            self.image_handler.base_image_dir = output_dir / "images"
            transformed_posts = self._process_images_for_obsidian(transformed_posts)
            
            # Show image statistics
            stats = self.image_handler.get_image_stats()
            console.print(f"   Downloaded images for {stats['total_posts']} posts")
            console.print(f"   Total images: {stats['total_images']} ({stats['total_size_mb']} MB)")
            
        console.print()
        
        # Phase 5: Generate files
        if dry_run:
            console.print("🔍 [yellow]Phase 5: Dry run - showing what would be generated...[/yellow]")
            self._show_dry_run_output(transformed_posts, output_dir)
        else:
            console.print("📄 [blue]Phase 5: Generating Obsidian files...[/blue]")
            self._generate_files(transformed_posts, output_dir)
            
        console.print()
        console.print("✅ [bold green]Conversion completed successfully![/bold green]")
        
        # Show summary
        self._show_summary(transformed_posts, output_dir, dry_run)
        
    def _generate_files(self, posts: list, output_dir: Path) -> None:
        """Generate all output files."""
        # Create directory structure for migration compatibility
        posts_dir = output_dir / "posts"
        drafts_dir = output_dir / "drafts"
        templates_dir = output_dir / "templates"
        images_dir = output_dir / "images" / "posts"
        
        # Create all required directories
        for directory in [posts_dir, drafts_dir, templates_dir, images_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Generate post files (basic implementation for now)
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("Generating post files", total=len(posts))
            
            for post in posts:
                # Determine if post is draft or published
                is_draft = 'draft' in post.get('status', [])
                target_dir = drafts_dir if is_draft else posts_dir
                
                post_file = target_dir / f"{post['slug']}.md"
                content = self.transformer.generate_obsidian_markdown(post)
                
                with open(post_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
                progress.advance(task)
                
        console.print(f"   Generated {len(posts)} post files")
        
    def _generate_basic_markdown(self, post: dict) -> str:
        """Generate basic markdown file (temporary implementation)."""
        frontmatter_lines = ['---']
        
        frontmatter_lines.append(f'title: "{post["title"]}"')
        if post.get('brief'):
            frontmatter_lines.append(f'description: "{post["brief"]}"')
        if post.get('dateAdded'):
            date = post['dateAdded'].split('T')[0]  # Extract YYYY-MM-DD
            frontmatter_lines.append(f'date: {date}')
        if post.get('slug'):
            frontmatter_lines.append(f'slug: "{post["slug"]}"')
        
        # Tags (simplified for now)
        if post.get('tags'):
            tag_names = []
            for tag in post['tags']:
                if isinstance(tag, dict):
                    tag_names.append(tag.get('name', tag.get('id', '')))
                else:
                    tag_names.append(str(tag))
            if tag_names:
                frontmatter_lines.append(f'tags:')
                for tag in tag_names:
                    frontmatter_lines.append(f'  - {tag}')
        
        # Series (simplified)
        if post.get('series'):
            series_name = post['series']
            if isinstance(series_name, dict):
                series_name = series_name.get('name', series_name.get('id', ''))
            frontmatter_lines.append(f'series: "{series_name}"')
        
        frontmatter_lines.append('---')
        frontmatter_lines.append('')
        
        # Content
        content = post.get('content', '')
        
        return '\n'.join(frontmatter_lines) + content
        
    def _show_dry_run_output(self, posts: list, output_dir: Path) -> None:
        """Show what would be generated in dry run mode."""
        console.print(f"   Would create {len(posts)} post files in: {output_dir}/posts/")
        
        if posts:
            console.print("\n   Sample posts that would be generated:")
            for i, post in enumerate(posts[:3]):
                console.print(f"   - {post['slug']}.md")
                if i == 2 and len(posts) > 3:
                    console.print(f"   ... and {len(posts) - 3} more")
                    break
                    
    def _show_summary(self, posts: list, output_dir: Path, dry_run: bool) -> None:
        """Show final summary."""
        console.print("\n📈 [bold blue]Conversion Summary:[/bold blue]")
        console.print(f"   Total posts processed: {len(posts)}")
        
        # Count posts with various features
        posts_with_tags = len([p for p in posts if p.get('tags')])
        posts_with_series = len([p for p in posts if p.get('series')])
        posts_with_images = len([p for p in posts if p.get('coverImage')])
        
        console.print(f"   Posts with tags: {posts_with_tags}")
        console.print(f"   Posts with series: {posts_with_series}")
        console.print(f"   Posts with cover images: {posts_with_images}")
        
        if not dry_run:
            console.print(f"\n🎉 [bold green]Files generated in: {output_dir}[/bold green]")
            console.print("   Ready for Obsidian!")
            
    def _process_images_for_obsidian(self, posts: list) -> list:
        """Process images for posts using the new Obsidian-compatible folder structure."""
        if not posts:
            return posts
            
        console.print(f"[blue]Processing images for {len(posts)} posts...[/blue]")
        
        updated_posts = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("Processing post images", total=len(posts))
            
            for post in posts:
                try:
                    post_slug = post.get('slug', 'unknown')
                    updated_post = self._download_post_images_obsidian(post, post_slug)
                    updated_posts.append(updated_post)
                except Exception as e:
                    console.print(f"[red]Failed to process images for post {post.get('slug', 'unknown')}: {e}[/red]")
                    updated_posts.append(post)  # Use original if processing fails
                    
                progress.advance(task)
                
        return updated_posts
        
    def _download_post_images_obsidian(self, post: Dict[str, Any], post_slug: str) -> Dict[str, Any]:
        """Download images for a post using Obsidian-compatible paths."""
        # Create post-specific image directory: images/posts/slug/
        post_image_dir = self.image_handler.base_image_dir / "posts" / post_slug
        post_image_dir.mkdir(parents=True, exist_ok=True)
        
        updated_post = post.copy()
        
        # Download cover image
        if post.get('cover_image'):
            cover_url = self._download_cover_image_obsidian(post['cover_image'], post_image_dir, post_slug)
            if cover_url:
                updated_post['cover_image'] = cover_url
                
        # Download content images and update references
        if post.get('content'):
            updated_content = self._download_content_images_obsidian(
                post['content'], 
                post_image_dir,
                post_slug
            )
            updated_post['content'] = updated_content
            
        return updated_post
        
    def _download_cover_image_obsidian(self, cover_url: str, post_dir: Path, post_slug: str) -> Optional[str]:
        """Download cover image and return Obsidian-compatible path."""
        if not cover_url or not cover_url.startswith(('http://', 'https://')):
            return cover_url
            
        try:
            local_path = self.image_handler._download_image(cover_url, post_dir, "cover")
            if local_path:
                # Return relative path for Obsidian: ../images/posts/slug/cover.jpg
                return f"../images/posts/{post_slug}/{local_path.name}"
        except Exception as e:
            console.print(f"[red]Failed to download cover image: {e}[/red]")
            
        return cover_url  # Return original URL if download fails
        
    def _download_content_images_obsidian(self, content: str, post_dir: Path, post_slug: str) -> str:
        """Download images referenced in content and update URLs for Obsidian."""
        if not content:
            return content
            
        # Extract image URLs from content using existing transformer
        image_urls = self.transformer.formatter.extract_images_from_content(content)
        
        if not image_urls:
            return content
            
        console.print(f"[blue]Found {len(image_urls)} images in post content[/blue]")
        
        updated_content = content
        
        for i, image_url in enumerate(image_urls):
            try:
                local_path = self.image_handler._download_image(image_url, post_dir, f"image-{i+1}")
                if local_path:
                    # Update content with Obsidian-compatible relative path
                    relative_path = f"../images/posts/{post_slug}/{local_path.name}"
                    updated_content = updated_content.replace(image_url, relative_path)
                    
            except Exception as e:
                console.print(f"[yellow]Failed to download {image_url}: {e}[/yellow]")
                
        return updated_content


if __name__ == '__main__':
    cli()