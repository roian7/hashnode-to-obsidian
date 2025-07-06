"""
Image handler module.

Downloads and processes images from Hashnode CDN and organizes them locally.
"""

import os
import requests
from pathlib import Path
from urllib.parse import urlparse
from typing import List, Optional, Dict, Any
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

console = Console()


class ImageHandler:
    """Handles downloading and organizing images for posts."""
    
    def __init__(self, base_image_dir: str = "./images"):
        """Initialize image handler with base directory."""
        self.base_image_dir = Path(base_image_dir)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Hashnode-to-11ty/1.0)'
        })
        
    def download_post_images(self, post: Dict[str, Any], post_slug: str) -> Dict[str, Any]:
        """Download all images for a post and update URLs."""
        post_image_dir = self.base_image_dir / "posts" / post_slug
        post_image_dir.mkdir(parents=True, exist_ok=True)
        
        updated_post = post.copy()
        
        # Download cover image
        if post.get('coverImage'):
            cover_url = self._download_cover_image(post['coverImage'], post_image_dir)
            if cover_url:
                updated_post['coverImage'] = cover_url
                
        # Download content images
        if post.get('content'):
            updated_content = self._download_content_images(
                post['content'], 
                post_image_dir,
                post_slug
            )
            updated_post['content'] = updated_content
            
        return updated_post
        
    def _download_cover_image(self, cover_url: str, post_dir: Path) -> Optional[str]:
        """Download cover image and return local path."""
        if not cover_url or not cover_url.startswith(('http://', 'https://')):
            return cover_url
            
        try:
            local_path = self._download_image(cover_url, post_dir, "cover")
            if local_path:
                # Return relative path for 11ty
                relative_path = f"/images/posts/{post_dir.name}/{local_path.name}"
                return relative_path
        except Exception as e:
            console.print(f"[red]Failed to download cover image: {e}[/red]")
            
        return cover_url  # Return original URL if download fails
        
    def _download_content_images(self, content: str, post_dir: Path, post_slug: str) -> str:
        """Download images referenced in content and update URLs."""
        if not content:
            return content
            
        # Find all image URLs in content
        from .transformer import ContentTransformer
        transformer = ContentTransformer()
        image_urls = transformer.extract_images_from_content(content)
        
        if not image_urls:
            return content
            
        console.print(f"[blue]Found {len(image_urls)} images in post content[/blue]")
        
        updated_content = content
        
        # Use a separate console instance to avoid conflicts with main progress bars
        image_console = Console()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=image_console
        ) as progress:
            
            task = progress.add_task(f"Downloading images for {post_slug}", total=len(image_urls))
            
            for i, image_url in enumerate(image_urls):
                try:
                    local_path = self._download_image(image_url, post_dir, f"content_{i+1}")
                    if local_path:
                        # Update content with local path
                        relative_path = f"/images/posts/{post_slug}/{local_path.name}"
                        updated_content = updated_content.replace(image_url, relative_path)
                        
                except Exception as e:
                    console.print(f"[yellow]Failed to download {image_url}: {e}[/yellow]")
                    
                progress.advance(task)
                
        return updated_content
        
    def _download_image(self, url: str, dest_dir: Path, base_name: str) -> Optional[Path]:
        """Download a single image and return local path."""
        try:
            # Parse URL to get file extension
            parsed_url = urlparse(url)
            original_name = Path(parsed_url.path).name
            
            # Determine file extension
            if '.' in original_name:
                ext = '.' + original_name.split('.')[-1].lower()
                # Validate extension
                valid_exts = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'}
                if ext not in valid_exts:
                    ext = '.jpg'  # Default fallback
            else:
                ext = '.jpg'  # Default if no extension
                
            # Generate local filename
            filename = f"{base_name}{ext}"
            local_path = dest_dir / filename
            
            # Skip if already downloaded
            if local_path.exists():
                return local_path
                
            # Download the image
            response = self.session.get(url, timeout=30, stream=True)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                console.print(f"[yellow]Warning: {url} doesn't appear to be an image (content-type: {content_type})[/yellow]")
                
            # Write to file
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            # Verify file was written
            if local_path.stat().st_size == 0:
                local_path.unlink()  # Remove empty file
                return None
                
            return local_path
            
        except requests.exceptions.RequestException as e:
            console.print(f"[yellow]Network error downloading {url}: {e}[/yellow]")
            return None
        except Exception as e:
            console.print(f"[yellow]Error downloading {url}: {e}[/yellow]")
            return None
            
    def batch_download_images(self, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Download images for multiple posts."""
        if not posts:
            return posts
            
        console.print(f"[blue]Processing images for {len(posts)} posts...[/blue]")
        
        updated_posts = []
        
        # Use a separate console instance to avoid conflicts with main progress bars  
        batch_console = Console()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=batch_console
        ) as progress:
            
            task = progress.add_task("Processing post images", total=len(posts))
            
            for post in posts:
                try:
                    post_slug = post.get('slug', 'unknown')
                    updated_post = self.download_post_images(post, post_slug)
                    updated_posts.append(updated_post)
                except Exception as e:
                    console.print(f"[red]Failed to process images for post {post.get('slug', 'unknown')}: {e}[/red]")
                    updated_posts.append(post)  # Use original if processing fails
                    
                progress.advance(task)
                
        return updated_posts
        
    def cleanup_post_images(self, post_slug: str) -> None:
        """Remove all images for a specific post."""
        post_dir = self.base_image_dir / "posts" / post_slug
        
        if post_dir.exists():
            try:
                # Remove all files in the directory
                for file_path in post_dir.iterdir():
                    if file_path.is_file():
                        file_path.unlink()
                        
                # Remove the directory
                post_dir.rmdir()
                console.print(f"[green]Cleaned up images for post: {post_slug}[/green]")
            except Exception as e:
                console.print(f"[yellow]Failed to cleanup images for {post_slug}: {e}[/yellow]")
                
    def get_image_stats(self) -> Dict[str, Any]:
        """Get statistics about downloaded images."""
        posts_dir = self.base_image_dir / "posts"
        
        if not posts_dir.exists():
            return {
                'total_posts': 0,
                'total_images': 0,
                'total_size_mb': 0.0
            }
            
        total_posts = 0
        total_images = 0
        total_size = 0
        
        for post_dir in posts_dir.iterdir():
            if post_dir.is_dir():
                total_posts += 1
                for image_file in post_dir.iterdir():
                    if image_file.is_file():
                        total_images += 1
                        total_size += image_file.stat().st_size
                        
        return {
            'total_posts': total_posts,
            'total_images': total_images,
            'total_size_mb': round(total_size / (1024 * 1024), 2)
        }